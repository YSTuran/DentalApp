from datetime import UTC, datetime, timedelta
from os import getenv

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models import (
    CaseStatus,
    CaseStatusHistory,
    CaseWaitAlert,
    DentalCase,
    EmailOutbox,
    Notification,
    RoleCode,
)
from app.services import email_dispatch
from app.services.case_waiting import create_overdue_case_alerts
from app.services.email_dispatch import dispatch_pending_emails
from app.services.notification_delivery import add_user_notification
from tests.integration.case_test_support import create_clinic, create_user

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        getenv("RUN_DATABASE_INTEGRATION_TESTS") != "1",
        reason="Set RUN_DATABASE_INTEGRATION_TESTS=1 to run database integration tests.",
    ),
]


def test_email_outbox_dispatches_a_queued_notification_once(
    case_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = create_user(case_session_factory, RoleCode.TECHNICIAN)
    with case_session_factory.begin() as session:
        notification = add_user_notification(
            session,
            recipient_user_id=user.id,
            actor_user_id=None,
            case_id=None,
            kind="test.email",
            title="Test bildirimi",
            message="VKA-TEST e-posta kuyruğu doğrulaması.",
            target_path="/vakalar/test",
        )
        assert notification is not None
        notification_id = notification.id

    sent_to: list[str] = []
    monkeypatch.setattr(
        email_dispatch,
        "_send_email",
        lambda item, _settings: sent_to.append(item.recipient_email),
    )
    with case_session_factory() as session:
        assert dispatch_pending_emails(session) == 1
        assert dispatch_pending_emails(session) == 0

    with case_session_factory() as session:
        item = session.scalar(
            select(EmailOutbox).where(EmailOutbox.notification_id == notification_id)
        )
        assert item is not None
        assert item.status == "sent"
        assert item.attempt_count == 1
        assert item.sent_at is not None
        assert sent_to == [user.email]


def test_waiting_warning_uses_status_history_and_is_not_duplicated(
    case_session_factory: sessionmaker[Session],
) -> None:
    clinic = create_clinic(case_session_factory, "WAIT")
    dentist = create_user(case_session_factory, RoleCode.DENTIST, clinic.id)
    manager = create_user(case_session_factory, RoleCode.MANAGING_DENTIST, clinic.id)
    stage_started_at = datetime.now(UTC) - timedelta(hours=25)

    with case_session_factory.begin() as session:
        dental_case = DentalCase(
            case_number="WAITING-TEST-001",
            clinic_id=clinic.id,
            created_by_user_id=dentist.id,
            responsible_dentist_user_id=dentist.id,
            status=CaseStatus.MANAGER_REVIEW,
        )
        session.add(dental_case)
        session.flush()
        session.add(
            CaseStatusHistory(
                case_id=dental_case.id,
                from_status=CaseStatus.DRAFT,
                to_status=CaseStatus.MANAGER_REVIEW,
                action="submit",
                actor_user_id=dentist.id,
                created_at=stage_started_at,
            )
        )
        case_id = dental_case.id

    with case_session_factory() as session:
        assert create_overdue_case_alerts(session) == 1
        assert create_overdue_case_alerts(session) == 0

    with case_session_factory() as session:
        alert = session.scalar(
            select(CaseWaitAlert).where(CaseWaitAlert.case_id == case_id)
        )
        notification = session.scalar(
            select(Notification).where(
                Notification.case_id == case_id,
                Notification.kind == "case.waiting_warning",
            )
        )
        assert alert is not None
        assert alert.recipient_user_id == manager.id
        assert alert.threshold_hours == 24
        assert notification is not None
        assert "24 saatten uzun" in notification.message
        assert session.scalar(
            select(EmailOutbox.id).where(
                EmailOutbox.notification_id == notification.id
            )
        ) is not None
