from datetime import UTC, datetime
from os import getenv
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies.auth import get_current_user
from app.main import app
from app.models import AuditEvent, RoleCode
from tests.integration.case_test_support import create_user

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        getenv("RUN_DATABASE_INTEGRATION_TESTS") != "1",
        reason="Set RUN_DATABASE_INTEGRATION_TESTS=1 to run database integration tests.",
    ),
]


def test_audit_events_can_be_filtered_by_inclusive_day_range(
    case_session_factory: sessionmaker[Session],
) -> None:
    admin = create_user(case_session_factory, RoleCode.SYSTEM_ADMIN)
    action = f"test.audit.date.{uuid4().hex}"
    with case_session_factory.begin() as session:
        session.add_all([
            AuditEvent(
                action=action,
                entity_type="test",
                entity_id="before",
                context_data={},
                created_at=datetime(2026, 10, 4, 23, 59, tzinfo=UTC),
            ),
            AuditEvent(
                action=action,
                entity_type="test",
                entity_id="inside",
                context_data={},
                created_at=datetime(2026, 10, 5, 12, 0, tzinfo=UTC),
            ),
            AuditEvent(
                action=action,
                entity_type="test",
                entity_id="upper-boundary",
                context_data={},
                created_at=datetime(2026, 10, 6, 0, 0, tzinfo=UTC),
            ),
        ])

    app.dependency_overrides[get_current_user] = lambda: admin
    with TestClient(app) as client:
        response = client.get(
            "/api/audit-events",
            params={
                "action": action,
                "created_from": "2026-10-05T00:00:00Z",
                "created_before": "2026-10-06T00:00:00Z",
            },
        )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert [item["entity_id"] for item in response.json()["items"]] == ["inside"]
