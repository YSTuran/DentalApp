from os import getenv
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies.auth import get_current_user
from app.main import app
from app.models import (
    AuditEvent,
    RoleCode,
)
from tests.integration.case_test_support import (
    create_clinic,
    create_ready_for_production_case,
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

def test_production_delivery_return_and_reproduction_cycle(
    case_session_factory: sessionmaker[Session],
) -> None:
    clinic = create_clinic(case_session_factory, "FULFILLMENT")
    dentist = create_user(case_session_factory, RoleCode.DENTIST, clinic.id)
    manager = create_user(case_session_factory, RoleCode.MANAGING_DENTIST, clinic.id)
    staff = create_user(case_session_factory, RoleCode.CLINIC_STAFF, clinic.id)
    technician = create_user(case_session_factory, RoleCode.TECHNICIAN)
    case, design = create_ready_for_production_case(
        case_session_factory,
        clinic_id=clinic.id,
        dentist_id=dentist.id,
        manager_id=manager.id,
        technician_id=technician.id,
    )

    with TestClient(app) as client:
        headers = csrf_headers(client)
        app.dependency_overrides[get_current_user] = lambda: technician
        started = client.post(
            f"/api/cases/{case.id}/production/start",
            headers=headers,
            json={"design_file_version_id": str(design.id), "notes": "İlk üretim"},
        )
        assert started.status_code == 200
        assert started.json()["status"] == "in_production"

        operations = client.get(f"/api/cases/{case.id}/operations")
        assert operations.status_code == 200
        first_run = operations.json()["production_runs"][0]
        assert first_run["attempt_number"] == 1
        assert first_run["work_order_number"].startswith("ISE-")
        assert "patient_name" not in operations.json()

        completed = client.post(
            f"/api/cases/{case.id}/production/complete",
            headers=headers,
            json={
                "production_run_id": first_run["id"],
                "material": "PET-G 1 mm",
                "lot_number": "LOT-2026-001",
                "quantity": 1,
            },
        )
        assert completed.status_code == 200
        assert completed.json()["status"] == "production_completed"

        shipped = client.post(
            f"/api/cases/{case.id}/shipments",
            headers=headers,
            json={
                "production_run_id": first_run["id"],
                "carrier": "Demo Kargo",
                "tracking_number": uuid4().hex,
            },
        )
        assert shipped.status_code == 200
        assert shipped.json()["status"] == "shipped"
        shipment_id = client.get(f"/api/cases/{case.id}/operations").json()["shipments"][0]["id"]

        app.dependency_overrides[get_current_user] = lambda: staff
        delivered = client.post(
            f"/api/cases/{case.id}/delivery-confirmation",
            headers=headers,
            json={"shipment_id": shipment_id, "notes": "Şubede teslim alındı."},
        )
        assert delivered.status_code == 200
        assert delivered.json()["status"] == "delivered"

        app.dependency_overrides[get_current_user] = lambda: technician
        returned = client.post(
            f"/api/cases/{case.id}/returns",
            headers=headers,
            json={
                "shipment_id": shipment_id,
                "reason_code": "fit_issue",
                "reason": "Aparey hastaya uyum sağlamadı.",
                "inspection_notes": "Üründe kırık bulunmuyor.",
            },
        )
        assert returned.status_code == 200
        assert returned.json()["status"] == "return_review"
        return_operations = client.get(f"/api/cases/{case.id}/operations").json()
        receipt_id = return_operations["return_receipts"][0]["id"]

        app.dependency_overrides[get_current_user] = lambda: manager
        decided = client.post(
            f"/api/cases/{case.id}/return-decision",
            headers=headers,
            json={
                "return_receipt_id": receipt_id,
                "resolution": "reproduction",
                "reason": "Yeni vaka ve yeni onay süreci oluşturulmalı.",
            },
        )
        assert decided.status_code == 200
        reproduction_case = decided.json()
        assert reproduction_case["id"] != str(case.id)
        assert reproduction_case["status"] == "draft"
        assert reproduction_case["reproduction_source_case_id"] == str(case.id)
        assert reproduction_case["file_versions"] == []
        assert reproduction_case["approvals"] == []
        assert reproduction_case["patient_code"] == "DEMO-FUL"

        app.dependency_overrides[get_current_user] = lambda: technician
        old_case = client.get(f"/api/cases/{case.id}")
        assert old_case.status_code == 200
        assert old_case.json()["status"] == "reproduction_requested"
        assert old_case.json()["reproduction_case_id"] == reproduction_case["id"]

        cannot_reuse_old_case = client.post(
            f"/api/cases/{case.id}/production/start",
            headers=headers,
            json={"design_file_version_id": str(design.id)},
        )
        assert cannot_reuse_old_case.status_code == 409
        final_operations = client.get(f"/api/cases/{case.id}/operations").json()
        assert [run["attempt_number"] for run in final_operations["production_runs"]] == [1]
        assert len(final_operations["return_decisions"]) == 1
        assert (
            final_operations["return_decisions"][0]["reproduction_case_id"]
            == reproduction_case["id"]
        )

    expected_actions = {
        "case.production_started",
        "case.production_completed",
        "case.shipped",
        "case.delivery_confirmed",
        "case.return_received",
        "case.reproduction_requested",
    }
    with case_session_factory() as session:
        actions = set(
            session.scalars(
                select(AuditEvent.action).where(AuditEvent.entity_id == str(case.id))
            ).all()
        )
    assert expected_actions.issubset(actions)
    with case_session_factory() as session:
        assert session.scalar(
            select(AuditEvent.id).where(
                AuditEvent.action == "case.created_from_return",
                AuditEvent.entity_id == reproduction_case["id"],
            )
        ) is not None
    immutable_rows = [
        ("UPDATE production_runs SET notes = 'changed' WHERE id = :id", first_run["id"]),
        (
            "DELETE FROM production_completions WHERE id = :id",
            final_operations["production_completions"][0]["id"],
        ),
        ("UPDATE shipments SET notes = 'changed' WHERE id = :id", shipment_id),
        (
            "DELETE FROM delivery_confirmations WHERE id = :id",
            final_operations["delivery_confirmations"][0]["id"],
        ),
        ("UPDATE return_receipts SET reason = 'changed' WHERE id = :id", receipt_id),
        (
            "DELETE FROM return_decisions WHERE id = :id",
            final_operations["return_decisions"][0]["id"],
        ),
    ]
    for mutation, record_id in immutable_rows:
        with case_session_factory() as session:
            with pytest.raises(DBAPIError, match="değiştirilemez veya silinemez"):
                session.execute(text(mutation), {"id": record_id})
                session.flush()
            session.rollback()


def test_production_requires_two_approvals(
    case_session_factory: sessionmaker[Session],
) -> None:
    clinic = create_clinic(case_session_factory, "FUL-NO-APPROVAL")
    dentist = create_user(case_session_factory, RoleCode.DENTIST, clinic.id)
    manager = create_user(case_session_factory, RoleCode.MANAGING_DENTIST, clinic.id)
    technician = create_user(case_session_factory, RoleCode.TECHNICIAN)
    case, design = create_ready_for_production_case(
        case_session_factory,
        clinic_id=clinic.id,
        dentist_id=dentist.id,
        manager_id=manager.id,
        technician_id=technician.id,
        with_dentist_approval=False,
    )
    app.dependency_overrides[get_current_user] = lambda: technician
    with TestClient(app) as client:
        response = client.post(
            f"/api/cases/{case.id}/production/start",
            headers=csrf_headers(client),
            json={"design_file_version_id": str(design.id)},
        )
    assert response.status_code == 409
    assert response.json()["detail"] == "case_two_approvals_required"

    with case_session_factory() as session:
        with pytest.raises(DBAPIError, match="onaylı ve kilitli tasarım"):
            session.execute(
                text(
                    """
                    INSERT INTO production_runs (
                        id, case_id, attempt_number, design_file_version_id,
                        work_order_number, started_by_user_id
                    ) VALUES (
                        :id, :case_id, 1, :design_id,
                        :work_order_number, :technician_id
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "case_id": case.id,
                    "design_id": design.id,
                    "work_order_number": f"TEST-{uuid4().hex[:12].upper()}",
                    "technician_id": technician.id,
                },
            )
            session.flush()
        session.rollback()
