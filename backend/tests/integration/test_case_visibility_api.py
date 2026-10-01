from os import getenv
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies.auth import get_current_user
from app.main import app
from app.models import (
    CaseDetail,
    CaseFileKind,
    CaseFileVersion,
    CaseStatus,
    CaseStatusHistory,
    DentalCase,
    MeshValidationStatus,
    RoleCode,
)
from tests.integration.case_test_support import create_clinic, create_user, csrf_headers

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        getenv("RUN_DATABASE_INTEGRATION_TESTS") != "1",
        reason="Set RUN_DATABASE_INTEGRATION_TESTS=1 to run database integration tests.",
    ),
]


def test_role_visibility_and_technician_patient_name_masking(
    case_session_factory: sessionmaker[Session],
) -> None:
    own_clinic = create_clinic(case_session_factory, "OWN")
    other_clinic = create_clinic(case_session_factory, "OTHER")
    own_dentist = create_user(case_session_factory, RoleCode.DENTIST, own_clinic.id)
    other_dentist = create_user(case_session_factory, RoleCode.DENTIST, other_clinic.id)
    manager = create_user(case_session_factory, RoleCode.CLINIC_MANAGER, own_clinic.id)
    technician = create_user(case_session_factory, RoleCode.TECHNICIAN)
    admin = create_user(case_session_factory, RoleCode.SYSTEM_ADMIN)

    with case_session_factory.begin() as session:
        draft = DentalCase(
            case_number=f"TEST-{uuid4().hex[:8]}",
            clinic_id=own_clinic.id,
            created_by_user_id=own_dentist.id,
            responsible_dentist_user_id=own_dentist.id,
            patient_code="P-DRAFT",
            patient_name="Gizli Taslak Hasta",
            status=CaseStatus.DRAFT,
            details=CaseDetail(),
        )
        lab_case = DentalCase(
            case_number=f"TEST-{uuid4().hex[:8]}",
            clinic_id=own_clinic.id,
            created_by_user_id=own_dentist.id,
            responsible_dentist_user_id=own_dentist.id,
            patient_code="P-LAB",
            patient_name="Gizli Laboratuvar Hastası",
            status=CaseStatus.LAB_DESIGN,
            details=CaseDetail(),
        )
        other_case = DentalCase(
            case_number=f"TEST-{uuid4().hex[:8]}",
            clinic_id=other_clinic.id,
            created_by_user_id=other_dentist.id,
            responsible_dentist_user_id=other_dentist.id,
            patient_code="P-OTHER",
            patient_name="Diğer Hasta",
            status=CaseStatus.DRAFT,
            details=CaseDetail(),
        )
        session.add_all([draft, lab_case, other_case])
        session.flush()
        session.add(
            CaseFileVersion(
                case_id=lab_case.id,
                kind=CaseFileKind.SCAN,
                version_number=1,
                original_filename="hasta-adi-tarama.stl",
                storage_key=f"test/{lab_case.id}/scan.stl",
                size_bytes=1024,
                sha256="b" * 64,
                mesh_status=MeshValidationStatus.VALID,
                uploaded_by_user_id=own_dentist.id,
            )
        )

    with TestClient(app) as client:
        app.dependency_overrides[get_current_user] = lambda: technician
        technician_list = client.get("/api/cases")
        technician_detail = client.get(f"/api/cases/{lab_case.id}")
        hidden_draft = client.get(f"/api/cases/{draft.id}")

        assert technician_list.status_code == 200
        assert [item["id"] for item in technician_list.json()["items"]] == [str(lab_case.id)]
        assert "patient_name" not in technician_list.json()["items"][0]
        assert "patient_name" not in technician_detail.json()
        assert "original_filename" not in technician_detail.json()["file_versions"][0]
        assert technician_detail.json()["patient_code"] == "P-LAB"
        assert hidden_draft.status_code == 403

        app.dependency_overrides[get_current_user] = lambda: manager
        manager_list = client.get("/api/cases")
        assert {item["id"] for item in manager_list.json()["items"]} == {
            str(draft.id),
            str(lab_case.id),
        }

        app.dependency_overrides[get_current_user] = lambda: other_dentist
        forbidden = client.get(f"/api/cases/{draft.id}")
        assert forbidden.status_code == 403

        app.dependency_overrides[get_current_user] = lambda: admin
        admin_list = client.get("/api/cases")
        assert {item["id"] for item in admin_list.json()["items"]} == {
            str(draft.id),
            str(lab_case.id),
            str(other_case.id),
        }


def test_case_creation_rejects_cross_clinic_responsible_dentist(
    case_session_factory: sessionmaker[Session],
) -> None:
    clinic = create_clinic(case_session_factory, "SOURCE")
    other_clinic = create_clinic(case_session_factory, "TARGET")
    staff = create_user(case_session_factory, RoleCode.CLINIC_STAFF, clinic.id)
    other_dentist = create_user(case_session_factory, RoleCode.DENTIST, other_clinic.id)
    app.dependency_overrides[get_current_user] = lambda: staff

    with TestClient(app) as client:
        response = client.post(
            "/api/cases",
            headers=csrf_headers(client),
            json={
                "clinic_id": str(clinic.id),
                "responsible_dentist_user_id": str(other_dentist.id),
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "case_responsible_dentist_invalid"

    with case_session_factory() as session:
        assert session.scalar(select(DentalCase.id)) is None
        assert session.scalar(select(CaseStatusHistory.id)) is None


def test_case_create_options_are_scoped_to_creator_clinics(
    case_session_factory: sessionmaker[Session],
) -> None:
    own_clinic = create_clinic(case_session_factory, "FORM")
    other_clinic = create_clinic(case_session_factory, "HIDDEN")
    staff = create_user(case_session_factory, RoleCode.CLINIC_STAFF, own_clinic.id)
    dentist = create_user(case_session_factory, RoleCode.DENTIST, own_clinic.id)
    manager_dentist = create_user(
        case_session_factory,
        RoleCode.MANAGING_DENTIST,
        own_clinic.id,
    )
    create_user(case_session_factory, RoleCode.DENTIST, other_clinic.id)

    app.dependency_overrides[get_current_user] = lambda: staff
    with TestClient(app) as client:
        response = client.get("/api/cases/create-options")

    assert response.status_code == 200
    assert response.json() == {
        "clinics": [
            {
                "id": str(own_clinic.id),
                "code": own_clinic.code,
                "name": own_clinic.name,
                "dentists": [
                    {"id": str(dentist.id), "full_name": dentist.full_name},
                    {
                        "id": str(manager_dentist.id),
                        "full_name": manager_dentist.full_name,
                    },
                ],
            }
        ]
    }
