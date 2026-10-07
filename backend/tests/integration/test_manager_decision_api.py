from os import getenv
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies.auth import get_current_user
from app.main import app
from app.models import (
    AuditEvent,
    CaseApproval,
    CaseDecision,
    CaseDetail,
    CaseFileKind,
    CaseFileVersion,
    CaseStatus,
    DentalCase,
    MeshValidationStatus,
    RoleCode,
)
from app.services.case_management.patient_data import set_patient_code
from tests.integration.case_test_support import create_clinic, create_user, csrf_headers

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        getenv("RUN_DATABASE_INTEGRATION_TESTS") != "1",
        reason="Set RUN_DATABASE_INTEGRATION_TESTS=1 to run database integration tests.",
    ),
]


def _create_review_case(
    factory: sessionmaker[Session],
    *,
    clinic_id,
    owner_id,
) -> tuple[DentalCase, CaseFileVersion]:
    with factory.begin() as session:
        case = DentalCase(
            case_number=f"MANAGER-{uuid4().hex[:10]}",
            clinic_id=clinic_id,
            created_by_user_id=owner_id,
            responsible_dentist_user_id=owner_id,
            status=CaseStatus.MANAGER_REVIEW,
            details=CaseDetail(
                appliance_type="Şeffaf plak",
                material="PET-G",
                tooth_numbers=["11"],
            ),
        )
        set_patient_code(case, "DEMO-MANAGER")
        session.add(case)
        session.flush()
        scan = CaseFileVersion(
            case_id=case.id,
            kind=CaseFileKind.SCAN,
            version_number=1,
            original_filename="manager-review.stl",
            storage_key=f"test/{case.id}/manager-review.stl",
            size_bytes=1024,
            sha256="c" * 64,
            mesh_status=MeshValidationStatus.VALID,
            uploaded_by_user_id=owner_id,
        )
        session.add(scan)
        session.flush()
    return case, scan


def test_manager_can_approve_latest_scan_and_lock_it(
    case_session_factory: sessionmaker[Session],
) -> None:
    clinic = create_clinic(case_session_factory, "MANAGER-APPROVE")
    owner = create_user(case_session_factory, RoleCode.DENTIST, clinic.id)
    manager = create_user(case_session_factory, RoleCode.MANAGING_DENTIST, clinic.id)
    case, scan = _create_review_case(
        case_session_factory,
        clinic_id=clinic.id,
        owner_id=owner.id,
    )
    app.dependency_overrides[get_current_user] = lambda: manager

    with TestClient(app) as client:
        response = client.post(
            f"/api/cases/{case.id}/manager-decision",
            headers=csrf_headers(client),
            json={
                "decision": "approved",
                "file_version_id": str(scan.id),
                "reason": "Üretim tasarımı için uygundur.",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "lab_design"
    assert body["file_versions"][0]["is_locked"] is True
    assert body["approvals"][0]["decision"] == "approved"
    assert body["approvals"][0]["is_self_approval"] is False

    with case_session_factory() as session:
        approval = session.scalar(
            select(CaseApproval).where(CaseApproval.case_id == case.id)
        )
        stored_scan = session.get(CaseFileVersion, scan.id)
        audit_action = session.scalar(
            select(AuditEvent.action).where(
                AuditEvent.entity_id == str(case.id),
                AuditEvent.action == "case.manager_approved",
            )
        )
    assert approval is not None
    assert stored_scan is not None and stored_scan.is_locked is True
    assert audit_action == "case.manager_approved"


def test_manager_revision_requires_reason_and_preserves_unlocked_scan(
    case_session_factory: sessionmaker[Session],
) -> None:
    clinic = create_clinic(case_session_factory, "MANAGER-REVISION")
    owner = create_user(case_session_factory, RoleCode.DENTIST, clinic.id)
    manager = create_user(case_session_factory, RoleCode.MANAGING_DENTIST, clinic.id)
    case, scan = _create_review_case(
        case_session_factory,
        clinic_id=clinic.id,
        owner_id=owner.id,
    )
    app.dependency_overrides[get_current_user] = lambda: manager

    with TestClient(app) as client:
        headers = csrf_headers(client)
        missing_reason = client.post(
            f"/api/cases/{case.id}/manager-decision",
            headers=headers,
            json={
                "decision": "revision_requested",
                "file_version_id": str(scan.id),
            },
        )
        response = client.post(
            f"/api/cases/{case.id}/manager-decision",
            headers=headers,
            json={
                "decision": "revision_requested",
                "file_version_id": str(scan.id),
                "reason": "Alt çenede tarama boşluğu bulunuyor.",
            },
        )

        app.dependency_overrides[get_current_user] = lambda: owner
        same_version_submit = client.post(
            f"/api/cases/{case.id}/submit",
            headers=headers,
        )

        with case_session_factory.begin() as session:
            session.add(
                CaseFileVersion(
                    case_id=case.id,
                    kind=CaseFileKind.SCAN,
                    version_number=2,
                    original_filename="manager-review-v2.stl",
                    storage_key=f"test/{case.id}/manager-review-v2.stl",
                    size_bytes=2048,
                    sha256="d" * 64,
                    mesh_status=MeshValidationStatus.VALID,
                    uploaded_by_user_id=owner.id,
                )
            )

        new_version_submit = client.post(
            f"/api/cases/{case.id}/submit",
            headers=headers,
        )

    assert missing_reason.status_code == 422
    assert response.status_code == 200
    assert response.json()["status"] == "manager_revision_requested"
    assert response.json()["file_versions"][0]["is_locked"] is False
    assert response.json()["approvals"][0]["decision"] == "revision_requested"
    assert same_version_submit.status_code == 422
    assert same_version_submit.json()["detail"] == "case_scan_revision_required"
    assert new_version_submit.status_code == 200
    assert new_version_submit.json()["status"] == "manager_review"


def test_manager_self_approval_is_marked(
    case_session_factory: sessionmaker[Session],
) -> None:
    clinic = create_clinic(case_session_factory, "MANAGER-SELF")
    manager = create_user(case_session_factory, RoleCode.MANAGING_DENTIST, clinic.id)
    case, scan = _create_review_case(
        case_session_factory,
        clinic_id=clinic.id,
        owner_id=manager.id,
    )
    app.dependency_overrides[get_current_user] = lambda: manager

    with TestClient(app) as client:
        response = client.post(
            f"/api/cases/{case.id}/manager-decision",
            headers=csrf_headers(client),
            json={"decision": CaseDecision.APPROVED, "file_version_id": str(scan.id)},
        )

    assert response.status_code == 200
    assert response.json()["approvals"][0]["is_self_approval"] is True


def test_responsible_manager_is_not_marked_as_self_approver_when_staff_created_case(
    case_session_factory: sessionmaker[Session],
) -> None:
    clinic = create_clinic(case_session_factory, "MANAGER-ASSIGNED")
    staff = create_user(case_session_factory, RoleCode.CLINIC_STAFF, clinic.id)
    manager = create_user(case_session_factory, RoleCode.MANAGING_DENTIST, clinic.id)
    case, scan = _create_review_case(
        case_session_factory,
        clinic_id=clinic.id,
        owner_id=manager.id,
    )
    with case_session_factory.begin() as session:
        stored_case = session.get(DentalCase, case.id)
        assert stored_case is not None
        stored_case.created_by_user_id = staff.id

    app.dependency_overrides[get_current_user] = lambda: manager
    with TestClient(app) as client:
        response = client.post(
            f"/api/cases/{case.id}/manager-decision",
            headers=csrf_headers(client),
            json={"decision": "approved", "file_version_id": str(scan.id)},
        )

    assert response.status_code == 200
    assert response.json()["approvals"][0]["is_self_approval"] is False


def test_manager_decision_rejects_wrong_clinic_and_stale_file_version(
    case_session_factory: sessionmaker[Session],
) -> None:
    clinic = create_clinic(case_session_factory, "MANAGER-SCOPE")
    other_clinic = create_clinic(case_session_factory, "MANAGER-OTHER")
    owner = create_user(case_session_factory, RoleCode.DENTIST, clinic.id)
    manager = create_user(case_session_factory, RoleCode.MANAGING_DENTIST, clinic.id)
    outsider = create_user(
        case_session_factory,
        RoleCode.MANAGING_DENTIST,
        other_clinic.id,
    )
    case, _scan = _create_review_case(
        case_session_factory,
        clinic_id=clinic.id,
        owner_id=owner.id,
    )

    with TestClient(app) as client:
        app.dependency_overrides[get_current_user] = lambda: outsider
        denied = client.post(
            f"/api/cases/{case.id}/manager-decision",
            headers=csrf_headers(client),
            json={"decision": "approved", "file_version_id": str(uuid4())},
        )

        app.dependency_overrides[get_current_user] = lambda: manager
        stale = client.post(
            f"/api/cases/{case.id}/manager-decision",
            headers=csrf_headers(client),
            json={"decision": "approved", "file_version_id": str(uuid4())},
        )

    assert denied.status_code == 403
    assert stale.status_code == 409
    assert stale.json()["detail"] == "case_scan_version_changed"
