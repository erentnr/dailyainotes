"""`dan`, the command line for operators and demos."""

import asyncio
from importlib.metadata import version as package_version
from pathlib import Path
from typing import Annotated

import typer

from dailyainotes.db.catalog import SyncCounts
from dailyainotes.db.engine import create_engine
from dailyainotes.db.migrate import upgrade_to_head
from dailyainotes.ingestion.catalog import CATALOG_PATH, load_catalog, sync_catalog
from dailyainotes.logging import configure_logging
from dailyainotes.settings import get_settings

app = typer.Typer(no_args_is_help=True, help="Daily AI Notes command line.")
db_app = typer.Typer(no_args_is_help=True, help="Database commands.")
catalog_app = typer.Typer(no_args_is_help=True, help="The topic catalog.")
app.add_typer(db_app, name="db")
app.add_typer(catalog_app, name="catalog")


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


@catalog_app.command("sync")
def catalog_sync(path: Annotated[Path, typer.Option(help="Catalog file.")] = CATALOG_PATH) -> None:
    """Load the catalog into the database. Adds and updates; never deletes."""
    counts = asyncio.run(_sync_catalog(path))
    typer.echo(
        f"{counts.topics} topics ({counts.active_topics} active), "
        f"{counts.publishers} publishers, {counts.sources} sources"
    )


async def _sync_catalog(path: Path) -> SyncCounts:
    engine = create_engine(get_settings().database_url)
    try:
        return await sync_catalog(engine, load_catalog(path))
    finally:
        await engine.dispose()
