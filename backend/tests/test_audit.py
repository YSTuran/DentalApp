from datetime import UTC, datetime
from uuid import uuid4

from starlette.requests import Request

from app.models import AuditEvent, User
from app.services.audit import record_audit_event


class RecordingSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.flush_count = 0

    def add(self, instance: object) -> None:
        self.added.append(instance)

    def flush(self) -> None:
        self.flush_count += 1


def test_record_audit_event_captures_actor_request_and_json_data() -> None:
    user = User(
        id=uuid4(),
        firebase_uid="audit-user",
        email="audit@example.invalid",
        full_name="Audit User",
    )
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/test",
            "headers": [(b"user-agent", b"DentalApp test")],
            "client": ("127.0.0.1", 50000),
        }
    )
    session = RecordingSession()

    event = record_audit_event(
        session,  # type: ignore[arg-type]
        action="test.updated",
        entity_type="test_entity",
        entity_id=uuid4(),
        actor=user,
        before={"status": "old"},
        after={"status": "new", "at": datetime(2026, 9, 24, tzinfo=UTC)},
        context={"source": "unit_test"},
        request=request,
    )

    assert session.added == [event]
    assert session.flush_count == 1
    assert event.actor_user_id == user.id
    assert event.actor_email == user.email
    assert event.after_data == {"status": "new", "at": "2026-09-24T00:00:00+00:00"}
    assert event.context_data == {"source": "unit_test"}
    assert event.ip_address == "127.0.0.1"
    assert event.user_agent == "DentalApp test"


def test_audit_event_has_no_updated_at_column() -> None:
    assert "created_at" in AuditEvent.__table__.columns
    assert "updated_at" not in AuditEvent.__table__.columns


def test_record_audit_event_supports_system_actor() -> None:
    session = RecordingSession()

    event = record_audit_event(
        session,  # type: ignore[arg-type]
        action="system.started",
        entity_type="system",
        entity_id="dentalapp",
        context={"source": "scheduler"},
    )

    assert event.actor_user_id is None
    assert event.actor_email is None
