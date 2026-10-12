from collections.abc import AsyncIterator, Iterator

import psycopg
import pytest
from psycopg import sql
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine

from dailyainotes.db.engine import create_engine
from dailyainotes.db.migrate import upgrade_to_head
from dailyainotes.db.tables import Base
from dailyainotes.settings import get_settings

TEST_DATABASE = "dailyainotes_test"


@pytest.fixture(scope="session")
def database_url() -> str:
    """A fresh test database, migrated to head, recreated once per test run."""
    url = make_url(get_settings().database_url)
    maintenance = url.set(drivername="postgresql", database="postgres")
    try:
        connection = psycopg.connect(
            maintenance.render_as_string(hide_password=False), autocommit=True, connect_timeout=3
        )
    except psycopg.OperationalError as error:
        pytest.fail(f"Postgres is not reachable at {url.host}:{url.port}; run `make up`. {error}")
    with connection:
        name = sql.Identifier(TEST_DATABASE)
        connection.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(name))
        connection.execute(sql.SQL("CREATE DATABASE {}").format(name))
    test_url = url.set(database=TEST_DATABASE).render_as_string(hide_password=False)
    upgrade_to_head(test_url)
    return test_url


@pytest.fixture
async def engine(database_url: str) -> AsyncIterator[AsyncEngine]:
    """An engine on an empty test database: every app table is truncated first."""
    engine = create_engine(database_url)
    tables = ", ".join(table.name for table in Base.metadata.sorted_tables)
    async with engine.begin() as connection:
        await connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    yield engine
    await engine.dispose()


@pytest.fixture
def settings_from_env() -> Iterator[None]:
    """Make `get_settings()` re-read the environment a test has changed, before and after."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
