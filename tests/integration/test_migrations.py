import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from typer.testing import CliRunner

from dailyainotes.cli import app
from dailyainotes.db.migrate import alembic_config
from dailyainotes.db.tables import Base

pytestmark = pytest.mark.integration


def test_the_migrations_create_exactly_what_the_models_describe(database_url: str) -> None:
    engine = create_engine(database_url)
    with engine.connect() as connection:
        differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    engine.dispose()

    assert differences == []


def test_the_baseline_installs_pgvector(database_url: str) -> None:
    engine = create_engine(database_url)
    with engine.connect() as connection:
        version = connection.execute(
            text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        ).scalar_one()
    engine.dispose()

    assert version.startswith("0.8.")


@pytest.mark.usefixtures("settings_from_env")
def test_dan_db_upgrade_is_safe_to_rerun(
    database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", database_url)

    result = CliRunner().invoke(app, ["db", "upgrade"])

    assert result.exit_code == 0, result.output
    engine = create_engine(database_url)
    with engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    engine.dispose()
    head = ScriptDirectory.from_config(alembic_config(database_url)).get_current_head()
    assert revision == head
