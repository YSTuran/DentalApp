from os import getenv

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies.auth import get_current_user
from app.main import app
from app.models import AuditEvent, RoleCode, UserPreference
from tests.integration.case_test_support import create_user, csrf_headers

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        getenv("RUN_DATABASE_INTEGRATION_TESTS") != "1",
        reason="Set RUN_DATABASE_INTEGRATION_TESTS=1 to run database integration tests.",
    ),
]


def test_user_can_store_theme_preferences_with_audit(
    case_session_factory: sessionmaker[Session],
) -> None:
    actor = create_user(case_session_factory, RoleCode.SYSTEM_ADMIN)
    app.dependency_overrides[get_current_user] = lambda: actor

    with TestClient(app) as client:
        default_response = client.get("/api/account/preferences")
        assert default_response.status_code == 200
        assert default_response.json() == {
            "theme_mode": "light",
            "color_palette": "default",
            "active_clinic_id": None,
            "updated_at": None,
        }

        missing_csrf = client.patch(
            "/api/account/preferences",
            json={"theme_mode": "dark"},
        )
        assert missing_csrf.status_code == 403

        update_response = client.patch(
            "/api/account/preferences",
            headers=csrf_headers(client),
            json={"theme_mode": "dark", "color_palette": "ocean"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["theme_mode"] == "dark"
        assert update_response.json()["color_palette"] == "ocean"

        stored_response = client.get("/api/account/preferences")
        assert stored_response.status_code == 200
        assert stored_response.json()["theme_mode"] == "dark"
        assert stored_response.json()["color_palette"] == "ocean"

        invalid_response = client.patch(
            "/api/account/preferences",
            headers=csrf_headers(client),
            json={"color_palette": "invalid"},
        )
        assert invalid_response.status_code == 422

        unchanged_response = client.patch(
            "/api/account/preferences",
            headers=csrf_headers(client),
            json={"theme_mode": "dark"},
        )
        assert unchanged_response.status_code == 200

    with case_session_factory() as session:
        preference = session.get(UserPreference, actor.id)
        audit_count = session.scalar(
            select(func.count())
            .select_from(AuditEvent)
            .where(
                AuditEvent.entity_id == str(actor.id),
                AuditEvent.action == "user.preferences.updated",
            )
        )

    assert preference is not None
    assert preference.theme_mode == "dark"
    assert preference.color_palette == "ocean"
    assert audit_count == 1
