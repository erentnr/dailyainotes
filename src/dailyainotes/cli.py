"""`dan`, the command line for operators and demos."""

from importlib.metadata import version as package_version

import typer

from dailyainotes.db.migrate import upgrade_to_head
from dailyainotes.logging import configure_logging
from dailyainotes.settings import get_settings

app = typer.Typer(no_args_is_help=True, help="Daily AI Notes command line.")
db_app = typer.Typer(no_args_is_help=True, help="Database commands.")
app.add_typer(db_app, name="db")


@app.callback()
def main() -> None:
    """Daily AI Notes command line."""
    configure_logging(get_settings().log_level)


@app.command()
def version() -> None:
    """Print the installed version."""
    typer.echo(package_version("dailyainotes"))


@db_app.command("upgrade")
def db_upgrade() -> None:
    """Apply every migration not yet applied. Safe to re-run."""
    upgrade_to_head(get_settings().database_url)
