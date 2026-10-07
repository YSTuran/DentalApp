from os import getenv

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies.auth import get_current_user
from app.main import app
from app.models import AuditEvent, DentalCase, EmailOutbox, Notification, RoleCode
from app.services.case_notifications import create_case_notifications
from tests.integration.case_test_support import create_clinic, create_user, csrf_headers

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        getenv("RUN_DATABASE_INTEGRATION_TESTS") != "1",
        reason="Set RUN_DATABASE_INTEGRATION_TESTS=1 to run database integration tests.",
    ),
]


def test_notification_is_private_and_dismissal_keeps_database_record(
    case_session_factory: sessionmaker[Session],
) -> None:
    clinic = create_clinic(case_session_factory, "NOTIFY")
    dentist = create_user(case_session_factory, RoleCode.DENTIST, clinic.id)
    manager = create_user(case_session_factory, RoleCode.MANAGING_DENTIST, clinic.id)
    with case_session_factory.begin() as session:
        notification = Notification(
            recipient_user_id=dentist.id,
            actor_user_id=manager.id,
            kind="case.manager_revision_requested",
            title="Tarama düzeltmesi istendi",
            message="TEST-001 için yeni tarama gerekiyor.",
            target_path="/vakalar/00000000-0000-0000-0000-000000000001",
        )
        session.add(notification)
        session.flush()
        notification_id = notification.id

    with TestClient(app) as client:
        app.dependency_overrides[get_current_user] = lambda: manager
        manager_list = client.get("/api/notifications")
        assert manager_list.json() == {"items": [], "total": 0}

        app.dependency_overrides[get_current_user] = lambda: dentist
        dentist_list = client.get("/api/notifications")
        assert dentist_list.status_code == 200
        assert dentist_list.json()["total"] == 1
        assert dentist_list.json()["items"][0]["id"] == str(notification_id)

        missing_csrf = client.post(f"/api/notifications/{notification_id}/dismiss")
        assert missing_csrf.status_code == 403
        assert missing_csrf.json()["detail"] == "csrf_validation_failed"

        dismissed = client.post(
            f"/api/notifications/{notification_id}/dismiss",
            headers=csrf_headers(client),
        )
        assert dismissed.status_code == 200
        assert client.get("/api/notifications").json() == {"items": [], "total": 0}

    with case_session_factory() as session:
        stored = session.get(Notification, notification_id)
        assert stored is not None
        assert stored.dismissed_at is not None
        assert session.scalar(
            select(AuditEvent.id).where(
                AuditEvent.action == "notification.dismissed",
                AuditEvent.entity_id == str(notification_id),
            )
        ) is not None


def test_case_notifications_are_routed_to_relevant_roles(
    case_session_factory: sessionmaker[Session],
) -> None:
    clinic = create_clinic(case_session_factory, "ROUTE")
    dentist = create_user(case_session_factory, RoleCode.DENTIST, clinic.id)
    manager = create_user(case_session_factory, RoleCode.MANAGING_DENTIST, clinic.id)
    technician = create_user(case_session_factory, RoleCode.TECHNICIAN)
    with case_session_factory.begin() as session:
        dental_case = DentalCase(
            case_number="NOTIFICATION-ROUTE-001",
            clinic_id=clinic.id,
            created_by_user_id=dentist.id,
            responsible_dentist_user_id=dentist.id,
        )
        session.add(dental_case)
        session.flush()
        create_case_notifications(
            session,
            case=dental_case,
            action="case.submitted",
            actor=dentist,
        )
        create_case_notifications(
            session,
            case=dental_case,
            action="case.manager_approved",
            actor=manager,
        )

    with case_session_factory() as session:
        notifications = session.scalars(
            select(Notification).where(Notification.case_id == dental_case.id)
        ).all()
        assert {
            ("case.submitted", manager.id),
            ("case.manager_approved", technician.id),
        }.issubset({(item.kind, item.recipient_user_id) for item in notifications})
        outbox = session.scalars(
            select(EmailOutbox).where(EmailOutbox.notification_id.in_(
                [item.id for item in notifications]
            ))
        ).all()
        assert {
            manager.email,
            technician.email,
        }.issubset({item.recipient_email for item in outbox})
        assert all(item.status == "pending" for item in outbox)
        assert all("patient" not in item.body_text.lower() for item in outbox)
