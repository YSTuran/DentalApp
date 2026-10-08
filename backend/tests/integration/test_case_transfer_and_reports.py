from os import getenv
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.api.dependencies.auth import get_current_user
from app.main import app
from app.models import (
    AuditEvent,
    CaseDetail,
    CaseStatus,
    DentalCase,
    Notification,
    RoleCode,
    User,
    UserPreference,
    UserRoleAssignment,
)
from app.services.case_notifications import create_case_notifications
from tests.integration.case_test_support import create_clinic, create_user, csrf_headers

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        getenv("RUN_DATABASE_INTEGRATION_TESTS") != "1",
        reason="Set RUN_DATABASE_INTEGRATION_TESTS=1 to run database integration tests.",
    ),
]


def _reload_user(factory: sessionmaker[Session], user_id) -> User:
    with factory() as session:
        user = session.scalar(
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.role_assignments),
                selectinload(User.clinic_assignments),
            )
        )
        assert user is not None
        return user


def test_roles_and_clinic_assignments_are_independent(
    case_session_factory: sessionmaker[Session],
) -> None:
    first = create_clinic(case_session_factory, "MULTI-A")
    second = create_clinic(case_session_factory, "MULTI-B")
    admin = create_user(case_session_factory, RoleCode.SYSTEM_ADMIN)
    manager = create_user(case_session_factory, RoleCode.CLINIC_MANAGER, first.id)
    dentist = create_user(case_session_factory, RoleCode.DENTIST, first.id)
    app.dependency_overrides[get_current_user] = lambda: admin

    with TestClient(app) as client:
        headers = csrf_headers(client)
        manager_clinic = client.post(
            f"/api/users/{manager.id}/clinics",
            headers=headers,
            json={
                "clinic_id": str(second.id),
                "reason": "İki şubeyi yönetiyor",
            },
        )
        dentist_clinic = client.post(
            f"/api/users/{dentist.id}/clinics",
            headers=headers,
            json={
                "clinic_id": str(second.id),
                "reason": "İkinci klinikte de çalışıyor",
            },
        )
        conflicting = client.post(
            f"/api/users/{manager.id}/roles",
            headers=headers,
            json={
                "role": "dentist",
                "reason": "Çakışan rol denemesi",
            },
        )

    assert manager_clinic.status_code == 201
    assert dentist_clinic.status_code == 201
    assert conflicting.status_code == 422
    assert conflicting.json()["detail"] == "conflicting_active_role"

    with case_session_factory() as session:
        session.add(
            UserRoleAssignment(
                user_id=manager.id,
                role=RoleCode.TECHNICIAN,
                is_active=True,
            )
        )
        with pytest.raises(DBAPIError):
            session.flush()
        session.rollback()

    reloaded_manager = _reload_user(case_session_factory, manager.id)
    app.dependency_overrides[get_current_user] = lambda: reloaded_manager
    with TestClient(app) as client:
        preference = client.patch(
            "/api/account/preferences",
            headers=csrf_headers(client),
            json={"active_clinic_id": str(second.id)},
        )
    assert preference.status_code == 200
    assert preference.json()["active_clinic_id"] == str(second.id)

    with case_session_factory() as session:
        stored = session.get(UserPreference, manager.id)
        assert stored is not None
        assert stored.active_clinic_id == second.id


def test_case_transfer_requires_target_acceptance_and_is_immutable(
    case_session_factory: sessionmaker[Session],
) -> None:
    clinic = create_clinic(case_session_factory, "TRANSFER")
    manager = create_user(case_session_factory, RoleCode.CLINIC_MANAGER, clinic.id)
    source = create_user(case_session_factory, RoleCode.DENTIST, clinic.id)
    target = create_user(case_session_factory, RoleCode.DENTIST, clinic.id)
    with case_session_factory.begin() as session:
        case = DentalCase(
            case_number=f"TRANSFER-{uuid4().hex[:8]}",
            clinic_id=clinic.id,
            created_by_user_id=source.id,
            responsible_dentist_user_id=source.id,
            status=CaseStatus.MANAGER_REVIEW,
            details=CaseDetail(),
        )
        session.add(case)
        session.flush()

    with TestClient(app) as client:
        headers = csrf_headers(client)
        app.dependency_overrides[get_current_user] = lambda: manager
        requested = client.post(
            f"/api/cases/{case.id}/transfers",
            headers=headers,
            json={
                "to_dentist_user_id": str(target.id),
                "reason": "Sorumlu hekim izinli",
            },
        )
        assert requested.status_code == 201
        transfer_id = requested.json()["id"]
        assert requested.json()["status"] == "pending"

        app.dependency_overrides[get_current_user] = lambda: target
        target_can_open = client.get(f"/api/cases/{case.id}")
        assert target_can_open.status_code == 200
        accepted = client.post(
            f"/api/cases/{case.id}/transfers/{transfer_id}/decision",
            headers=headers,
            json={"decision": "accepted"},
        )
        assert accepted.status_code == 200
        assert accepted.json()["status"] == "accepted"

        app.dependency_overrides[get_current_user] = lambda: source
        assert client.get(f"/api/cases/{case.id}").status_code == 403

        app.dependency_overrides[get_current_user] = lambda: target
        assert client.get(f"/api/cases/{case.id}").status_code == 200

    with case_session_factory() as session:
        stored_case = session.get(DentalCase, case.id)
        event = session.scalar(
            select(AuditEvent).where(
                AuditEvent.action == "case.transfer_accepted",
                AuditEvent.entity_id == transfer_id,
            )
        )
        assert stored_case is not None
        assert stored_case.responsible_dentist_user_id == target.id
        assert event is not None

        create_case_notifications(
            session,
            case=stored_case,
            action="case.reproduction_requested",
            actor=manager,
        )
        session.commit()
        reproduction_recipients = set(
            session.scalars(
                select(Notification.recipient_user_id).where(
                    Notification.case_id == case.id,
                    Notification.kind == "case.reproduction_requested",
                )
            ).all()
        )
        assert target.id in reproduction_recipients
        assert source.id not in reproduction_recipients

    with case_session_factory() as session:
        with pytest.raises(DBAPIError, match="cannot be deleted"):
            session.execute(
                text("DELETE FROM case_transfers WHERE id = :id"),
                {"id": transfer_id},
            )
            session.flush()
        session.rollback()


def test_report_respects_clinic_scope_and_contains_no_patient_identity(
    case_session_factory: sessionmaker[Session],
) -> None:
    own = create_clinic(case_session_factory, "REPORT-OWN")
    other = create_clinic(case_session_factory, "REPORT-OTHER")
    manager = create_user(case_session_factory, RoleCode.CLINIC_MANAGER, own.id)
    managing_dentist = create_user(
        case_session_factory,
        RoleCode.MANAGING_DENTIST,
        own.id,
    )
    dentist = create_user(case_session_factory, RoleCode.DENTIST, own.id)
    technician = create_user(case_session_factory, RoleCode.TECHNICIAN)
    other_dentist = create_user(case_session_factory, RoleCode.DENTIST, other.id)
    with case_session_factory.begin() as session:
        session.add_all(
            [
                DentalCase(
                    case_number=f"REPORT-{uuid4().hex[:8]}",
                    clinic_id=own.id,
                    created_by_user_id=dentist.id,
                    responsible_dentist_user_id=dentist.id,
                    status=CaseStatus.DRAFT,
                    details=CaseDetail(),
                ),
                DentalCase(
                    case_number=f"REPORT-{uuid4().hex[:8]}",
                    clinic_id=other.id,
                    created_by_user_id=other_dentist.id,
                    responsible_dentist_user_id=other_dentist.id,
                    status=CaseStatus.DELIVERED,
                    details=CaseDetail(),
                ),
            ]
        )

    app.dependency_overrides[get_current_user] = lambda: manager
    with TestClient(app) as client:
        response = client.get("/api/reports/cases")
        forbidden = client.get("/api/reports/cases", params={"clinic_id": str(other.id)})

    assert response.status_code == 200
    assert response.json()["totals"]["total"] == 1
    assert response.json()["clinic_counts"][0]["id"] == str(own.id)
    assert "patient" not in response.text.lower()
    assert forbidden.status_code == 403

    app.dependency_overrides[get_current_user] = lambda: managing_dentist
    with TestClient(app) as client:
        assert client.get("/api/reports/cases").status_code == 200

    app.dependency_overrides[get_current_user] = lambda: dentist
    with TestClient(app) as client:
        assert client.get("/api/reports/cases").status_code == 403

    app.dependency_overrides[get_current_user] = lambda: technician
    with TestClient(app) as client:
        assert client.get("/api/reports/cases").status_code == 403
