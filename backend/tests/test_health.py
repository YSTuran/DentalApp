from fastapi.testclient import TestClient

from app.api.routes import health
from app.main import app

client = TestClient(app)


def test_root_contains_demo_warning() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["demo_mode"] is True
    assert "Gerçek hasta verisi girmeyiniz" in response.json()["warning"]


def test_liveness() -> None:
    response = client.get("/api/health/live")

    assert response.status_code == 200
    assert response.json() == {"api": "ok", "demo_mode": True}


def test_readiness_when_dependencies_are_available(monkeypatch) -> None:
    monkeypatch.setattr(health, "check_database", lambda: True)
    monkeypatch.setattr(health, "check_redis", lambda: True)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "api": "ok",
        "database": "ok",
        "redis": "ok",
        "demo_mode": True,
    }


def test_readiness_returns_503_when_a_dependency_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(health, "check_database", lambda: False)
    monkeypatch.setattr(health, "check_redis", lambda: True)

    response = client.get("/api/health")

    assert response.status_code == 503
    assert response.json()["database"] == "error"
