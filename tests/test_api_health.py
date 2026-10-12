import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine

from dailyainotes.api import health
from dailyainotes.api.app import create_app
from dailyainotes.settings import Settings


def client_with_database(monkeypatch: pytest.MonkeyPatch, *, reachable: bool) -> TestClient:
    async def fake_database_is_reachable(engine: AsyncEngine) -> bool:
        return reachable

    monkeypatch.setattr(health, "database_is_reachable", fake_database_is_reachable)
    return TestClient(create_app(Settings(_env_file=None)))


def test_health_is_ok_when_the_database_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    with client_with_database(monkeypatch, reachable=True) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_is_503_when_the_database_is_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with client_with_database(monkeypatch, reachable=False) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": "unreachable"}
