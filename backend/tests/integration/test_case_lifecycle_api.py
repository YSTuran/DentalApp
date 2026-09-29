from os import getenv

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies.auth import get_current_user
from app.main import app
from app.models import (
    AuditEvent,
    CaseFileKind,
    CaseFileVersion,
    MeshValidationStatus,
    RoleCode,
)
from tests.integration.case_test_support import (
    create_case_payload,
    create_clinic,
    create_user,
    csrf_headers,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        getenv("RUN_DATABASE_INTEGRATION_TESTS") != "1",
        reason="Set RUN_DATABASE_INTEGRATION_TESTS=1 to run database integration tests.",
    ),
]


def test_case_draft_submit_history_and_audit(
    case_session_factory: sessionmaker[Session],
) -> None:
    clinic = create_clinic(case_session_factory, "FLOW")
    dentist = create_user(case_session_factory, RoleCode.DENTIST, clinic.id)
    staff = create_user(case_session_factory, RoleCode.CLINIC_STAFF, clinic.id)
    app.dependency_overrides[get_current_user] = lambda: staff

    with TestClient(app) as client:
        headers = csrf_headers(client)
        create_response = client.post(
            "/api/cases",
            headers=headers,
            json=create_case_payload(clinic, dentist),
        )
        assert create_response.status_code == 201
        created = create_response.json()
        case_id = created["id"]
        assert created["case_number"].startswith("VKA-")
        assert created["status"] == "draft"

        no_scan_response = client.post(f"/api/cases/{case_id}/submit", headers=headers)
        assert no_scan_response.status_code == 422
        assert no_scan_response.json()["detail"] == "case_scan_required"

    with case_session_factory.begin() as session:
        session.add(
            CaseFileVersion(
                case_id=case_id,
                kind=CaseFileKind.SCAN,
                version_number=1,
                original_filename="scan-v1.stl",
                storage_key=f"test/{case_id}/scan-v1.stl",
                size_bytes=2048,
                sha256="a" * 64,
                mesh_status=MeshValidationStatus.VALID,
                uploaded_by_user_id=staff.id,
            )
        )

    with TestClient(app) as client:
        headers = csrf_headers(client)
        update_response = client.patch(
            f"/api/cases/{case_id}",
            headers=headers,
            json={"patient_code": "HST-002", "reason": "Kod düzeltildi"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["patient_code"] == "HST-002"

        submit_response = client.post(f"/api/cases/{case_id}/submit", headers=headers)
        assert submit_response.status_code == 200
        assert submit_response.json()["status"] == "manager_review"

        repeat_response = client.post(f"/api/cases/{case_id}/submit", headers=headers)
        assert repeat_response.status_code == 409
        assert repeat_response.json()["detail"] == "case_invalid_transition"

        history_response = client.get(f"/api/cases/{case_id}/history")
        assert history_response.status_code == 200
        assert [item["action"] for item in history_response.json()["items"]] == [
            "create",
            "submit",
        ]

        delete_response = client.delete(f"/api/cases/{case_id}", headers=headers)
        assert delete_response.status_code == 405

    with case_session_factory() as session:
        actions = set(
            session.scalars(select(AuditEvent.action).where(AuditEvent.entity_id == case_id)).all()
        )
    assert actions == {"case.created", "case.updated", "case.submitted"}


def test_submit_rejects_incomplete_draft_and_cancel_preserves_record(
    case_session_factory: sessionmaker[Session],
) -> None:
    clinic = create_clinic(case_session_factory, "DRAFT")
    dentist = create_user(case_session_factory, RoleCode.DENTIST, clinic.id)
    app.dependency_overrides[get_current_user] = lambda: dentist

    with TestClient(app) as client:
        headers = csrf_headers(client)
        create_response = client.post(
            "/api/cases",
            headers=headers,
            json={
                "clinic_id": str(clinic.id),
                "responsible_dentist_user_id": str(dentist.id),
            },
        )
        assert create_response.status_code == 201
        case_id = create_response.json()["id"]

        submit_response = client.post(f"/api/cases/{case_id}/submit", headers=headers)
        assert submit_response.status_code == 422
        assert submit_response.json()["detail"]["code"] == "case_required_fields_missing"
        assert set(submit_response.json()["detail"]["fields"]) == {
            "patient_code",
            "appliance_type",
            "material",
            "tooth_numbers",
        }

        missing_reason = client.post(
            f"/api/cases/{case_id}/cancel",
            headers=headers,
            json={},
        )
        assert missing_reason.status_code == 422

        cancel_response = client.post(
            f"/api/cases/{case_id}/cancel",
            headers=headers,
            json={"reason": "Yanlış açılan demo vaka"},
        )
        assert cancel_response.status_code == 200
        assert cancel_response.json()["status"] == "cancelled"

        detail_response = client.get(f"/api/cases/{case_id}")
        assert detail_response.status_code == 200
        assert detail_response.json()["status"] == "cancelled"
