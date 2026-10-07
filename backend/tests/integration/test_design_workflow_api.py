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
    CaseApprovalType,
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


def _create_lab_case(
    factory: sessionmaker[Session],
    *,
    clinic_id,
    dentist_id,
    manager_id,
    with_manager_approval: bool = True,
) -> tuple[DentalCase, CaseFileVersion]:
    with factory.begin() as session:
        case = DentalCase(
            case_number=f"DESIGN-{uuid4().hex[:10]}",
            clinic_id=clinic_id,
            created_by_user_id=dentist_id,
            responsible_dentist_user_id=dentist_id,
            status=CaseStatus.LAB_DESIGN,
            details=CaseDetail(
                appliance_type="Şeffaf plak",
                material="PET-G",
                tooth_numbers=["11"],
            ),
        )
        set_patient_code(case, "DEMO-DESIGN")
        session.add(case)
        session.flush()
        scan = CaseFileVersion(
            case_id=case.id,
            kind=CaseFileKind.SCAN,
            version_number=1,
            original_filename="scan.stl",
            storage_key=f"test/{case.id}/scan.stl",
            size_bytes=1024,
            sha256="a" * 64,
            mesh_status=MeshValidationStatus.VALID,
            uploaded_by_user_id=dentist_id,
            is_locked=with_manager_approval,
        )
        session.add(scan)
        session.flush()
        if with_manager_approval:
            session.add(
                CaseApproval(
                    case_id=case.id,
                    approval_type=CaseApprovalType.MANAGER_SCAN,
                    decision=CaseDecision.APPROVED,
                    file_version_id=scan.id,
                    actor_user_id=manager_id,
                )
            )
        design = CaseFileVersion(
            case_id=case.id,
            kind=CaseFileKind.DESIGN,
            version_number=1,
            original_filename="design-v1.stl",
            storage_key=f"test/{case.id}/design-v1.stl",
            size_bytes=2048,
            sha256="b" * 64,
            mesh_status=MeshValidationStatus.VALID,
            uploaded_by_user_id=manager_id,
        )
        session.add(design)
        session.flush()
    return case, design


def test_design_revision_and_approval_require_new_version_and_responsible_dentist(
    case_session_factory: sessionmaker[Session],
) -> None:
    clinic = create_clinic(case_session_factory, "DESIGN-FLOW")
    dentist = create_user(case_session_factory, RoleCode.DENTIST, clinic.id)
    other_dentist = create_user(case_session_factory, RoleCode.DENTIST, clinic.id)
    manager = create_user(case_session_factory, RoleCode.MANAGING_DENTIST, clinic.id)
    technician = create_user(case_session_factory, RoleCode.TECHNICIAN)
    case, design_v1 = _create_lab_case(
        case_session_factory,
        clinic_id=clinic.id,
        dentist_id=dentist.id,
        manager_id=manager.id,
    )

    with TestClient(app) as client:
        headers = csrf_headers(client)
        app.dependency_overrides[get_current_user] = lambda: technician
        submitted = client.post(
            f"/api/cases/{case.id}/design-submit",
            headers=headers,
            json={"file_version_id": str(design_v1.id)},
        )
        assert submitted.status_code == 200
        assert submitted.json()["status"] == "dentist_review"

        app.dependency_overrides[get_current_user] = lambda: other_dentist
        denied = client.post(
            f"/api/cases/{case.id}/dentist-decision",
            headers=headers,
            json={"decision": "approved", "file_version_id": str(design_v1.id)},
        )
        assert denied.status_code == 403

        app.dependency_overrides[get_current_user] = lambda: dentist
        rejected = client.post(
            f"/api/cases/{case.id}/dentist-decision",
            headers=headers,
            json={
                "decision": "rejected",
                "file_version_id": str(design_v1.id),
                "reason": "Bu karar türü kullanılamaz.",
            },
        )
        assert rejected.status_code == 422

        missing_reason = client.post(
            f"/api/cases/{case.id}/dentist-decision",
            headers=headers,
            json={
                "decision": "revision_requested",
                "file_version_id": str(design_v1.id),
            },
        )
        assert missing_reason.status_code == 422

        revision = client.post(
            f"/api/cases/{case.id}/dentist-decision",
            headers=headers,
            json={
                "decision": "revision_requested",
                "file_version_id": str(design_v1.id),
                "reason": "Kenar kalınlığı düzeltilmeli.",
            },
        )
        assert revision.status_code == 200
        assert revision.json()["status"] == "design_revision_requested"

        app.dependency_overrides[get_current_user] = lambda: technician
        same_version = client.post(
            f"/api/cases/{case.id}/design-submit",
            headers=headers,
            json={"file_version_id": str(design_v1.id)},
        )
        assert same_version.status_code == 422
        assert same_version.json()["detail"] == "case_design_revision_required"

        with case_session_factory.begin() as session:
            design_v2 = CaseFileVersion(
                case_id=case.id,
                kind=CaseFileKind.DESIGN,
                version_number=2,
                original_filename="design-v2.stl",
                storage_key=f"test/{case.id}/design-v2.stl",
                size_bytes=3072,
                sha256="c" * 64,
                mesh_status=MeshValidationStatus.VALID,
                uploaded_by_user_id=technician.id,
            )
            session.add(design_v2)
            session.flush()

        resubmitted = client.post(
            f"/api/cases/{case.id}/design-submit",
            headers=headers,
            json={"file_version_id": str(design_v2.id)},
        )
        assert resubmitted.status_code == 200
        assert resubmitted.json()["status"] == "dentist_review"

        app.dependency_overrides[get_current_user] = lambda: dentist
        approved = client.post(
            f"/api/cases/{case.id}/dentist-decision",
            headers=headers,
            json={"decision": "approved", "file_version_id": str(design_v2.id)},
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == "ready_for_production"

    with case_session_factory() as session:
        stored_v1 = session.get(CaseFileVersion, design_v1.id)
        stored_v2 = session.get(CaseFileVersion, design_v2.id)
        actions = set(
            session.scalars(
                select(AuditEvent.action).where(AuditEvent.entity_id == str(case.id))
            ).all()
        )
    assert stored_v1 is not None and stored_v1.is_locked is False
    assert stored_v2 is not None and stored_v2.is_locked is True
    assert {
        "case.design_submitted",
        "case.design_revision_requested",
        "case.design_approved",
    }.issubset(actions)


def test_design_cannot_reach_dentist_without_manager_approval(
    case_session_factory: sessionmaker[Session],
) -> None:
    clinic = create_clinic(case_session_factory, "DESIGN-NO-MANAGER")
    dentist = create_user(case_session_factory, RoleCode.DENTIST, clinic.id)
    manager = create_user(case_session_factory, RoleCode.MANAGING_DENTIST, clinic.id)
    technician = create_user(case_session_factory, RoleCode.TECHNICIAN)
    case, design = _create_lab_case(
        case_session_factory,
        clinic_id=clinic.id,
        dentist_id=dentist.id,
        manager_id=manager.id,
        with_manager_approval=False,
    )
    app.dependency_overrides[get_current_user] = lambda: technician

    with TestClient(app) as client:
        response = client.post(
            f"/api/cases/{case.id}/design-submit",
            headers=csrf_headers(client),
            json={"file_version_id": str(design.id)},
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "case_manager_approval_required"
