from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.models import Clinic, RoleCode, User, UserRoleAssignment


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
