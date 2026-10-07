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
    RoleCode,
    User,
    UserPreference,
    UserRoleAssignment,
)
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
            .options(selectinload(User.role_assignments))
        )
        assert user is not None
        return user


def test_only_clinic_manager_can_span_multiple_clinics(
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
        allowed = client.post(
            f"/api/users/{manager.id}/roles",
            headers=headers,
            json={
                "role": "clinic_manager",
                "clinic_id": str(second.id),
                "reason": "İki şubeyi yönetiyor",
            },
        )
        denied = client.post(
            f"/api/users/{dentist.id}/roles",
            headers=headers,
            json={
                "role": "dentist",
                "clinic_id": str(second.id),
                "reason": "İkinci klinik denemesi",
            },
        )

    assert allowed.status_code == 201
    assert denied.status_code == 422
    assert denied.json()["detail"] == "multi_clinic_role_not_allowed"

    with case_session_factory() as session:
        session.add(
            UserRoleAssignment(
                user_id=dentist.id,
                role=RoleCode.CLINIC_MANAGER,
                clinic_id=second.id,
                is_active=True,
            )
        )
        with pytest.raises(DBAPIError, match="Only clinic managers"):
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
    dentist = create_user(case_session_factory, RoleCode.DENTIST, own.id)
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
