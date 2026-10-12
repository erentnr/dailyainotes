"""Run Alembic migrations from code, for `dan db upgrade` and the tests."""

from alembic import command
from alembic.config import Config


def alembic_config(database_url: str) -> Config:
    config = Config()
    config.set_main_option("script_location", "dailyainotes.db:migrations")
    # Passed as an attribute, not an ini option, so a "%" in a password is not interpolated.
    config.attributes["database_url"] = database_url
    return config


def upgrade_to_head(database_url: str) -> None:
    command.upgrade(alembic_config(database_url), "head")
