from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.models import (
    CaseApproval,
    CaseApprovalType,
    CaseDecision,
    CaseDetail,
    CaseFileKind,
    CaseFileVersion,
    CaseStatus,
    Clinic,
    DentalCase,
    MeshValidationStatus,
    RoleCode,
    User,
    UserRoleAssignment,
)


def create_clinic(factory: sessionmaker[Session], prefix: str) -> Clinic:
    with factory.begin() as session:
        clinic = Clinic(code=f"{prefix}-{uuid4().hex[:8]}", name=f"{prefix} Clinic")
        session.add(clinic)
        session.flush()
    return clinic


def create_user(
    factory: sessionmaker[Session],
    role: RoleCode,
    clinic_id=None,
) -> User:
    with factory.begin() as session:
        user = User(
            firebase_uid=uuid4().hex,
            email=f"{uuid4().hex}@example.invalid",
            full_name=f"Case Test {role.value}",
        )
        user.role_assignments = [UserRoleAssignment(role=role, clinic_id=clinic_id, is_active=True)]
        session.add(user)
        session.flush()
    return user


def csrf_headers(client: TestClient) -> dict[str, str]:
    response = client.get("/api/auth/csrf")
    return {"X-CSRF-Token": response.json()["csrf_token"]}


def create_case_payload(clinic: Clinic, dentist: User) -> dict[str, object]:
    return {
        "clinic_id": str(clinic.id),
        "responsible_dentist_user_id": str(dentist.id),
        "patient_code": "HST-001",
        "patient_name": "Demo Hasta",
        "appliance_type": "Şeffaf plak",
        "material": "PET-G",
        "tooth_numbers": ["11", "12", "21"],
        "special_notes": "Sadece demo verisidir.",
        "extra_fields": {"renk": "şeffaf"},
    }


def create_ready_for_production_case(
    factory: sessionmaker[Session],
    *,
    clinic_id,
    dentist_id,
    manager_id,
    technician_id,
    with_dentist_approval: bool = True,
) -> tuple[DentalCase, CaseFileVersion]:
    with factory.begin() as session:
        case = DentalCase(
            case_number=f"FUL-{uuid4().hex[:10]}",
            clinic_id=clinic_id,
            created_by_user_id=dentist_id,
            responsible_dentist_user_id=dentist_id,
            patient_code="DEMO-FUL",
            patient_name="Gizli Demo Hasta",
            status=CaseStatus.READY_FOR_PRODUCTION,
            details=CaseDetail(
                appliance_type="Şeffaf plak",
                material="PET-G",
                tooth_numbers=["11"],
            ),
        )
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
            is_locked=True,
        )
        design = CaseFileVersion(
            case_id=case.id,
            kind=CaseFileKind.DESIGN,
            version_number=1,
            original_filename="design.stl",
            storage_key=f"test/{case.id}/design.stl",
            size_bytes=2048,
            sha256="b" * 64,
            mesh_status=MeshValidationStatus.VALID,
            uploaded_by_user_id=technician_id,
            is_locked=True,
        )
        session.add_all([scan, design])
        session.flush()
        session.add(
            CaseApproval(
                case_id=case.id,
                approval_type=CaseApprovalType.MANAGER_SCAN,
                decision=CaseDecision.APPROVED,
                file_version_id=scan.id,
                actor_user_id=manager_id,
            )
        )
        if with_dentist_approval:
            session.add(
                CaseApproval(
                    case_id=case.id,
                    approval_type=CaseApprovalType.DENTIST_DESIGN,
                    decision=CaseDecision.APPROVED,
                    file_version_id=design.id,
                    actor_user_id=dentist_id,
                )
            )
    return case, design
