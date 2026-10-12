import pytest
from fastapi.testclient import TestClient

from dailyainotes.api.app import create_app
from dailyainotes.settings import Settings

pytestmark = pytest.mark.integration


def test_health_reaches_the_real_database(database_url: str) -> None:
    settings = Settings(_env_file=None, database_url=database_url)

    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_reports_a_database_that_is_down() -> None:
    # Nothing listens on port 1, so the connection is refused at once.
    settings = Settings(_env_file=None, database_url="postgresql+psycopg://dan:dan@127.0.0.1:1/x")

    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 503
