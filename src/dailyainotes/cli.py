"""`dan`, the command line for operators and demos."""

import asyncio
from datetime import UTC, datetime
from importlib.metadata import version as package_version
from pathlib import Path
from typing import Annotated

import typer

from dailyainotes.db.catalog import SyncCounts
from dailyainotes.db.engine import create_engine
from dailyainotes.db.ingest import active_topic_slugs, purge_expired_content
from dailyainotes.db.migrate import upgrade_to_head
from dailyainotes.ingestion.catalog import CATALOG_PATH, load_catalog, sync_catalog
from dailyainotes.ingestion.run import SourceReport, ingest_topic
from dailyainotes.llm.embeddings import LocalEmbeddings
from dailyainotes.logging import configure_logging
from dailyainotes.settings import get_settings
from dailyainotes.sources.http import create_http

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


@app.command()
def ingest(
    topic: Annotated[
        str | None, typer.Option(help="A topic slug; all active topics if left out.")
    ] = None,
) -> None:
    """Fetch new items for active topics and save them, searchable, with their text policy."""
    for slug, reports in asyncio.run(_ingest(topic)).items():
        typer.echo(f"\n{slug}")
        for report in reports:
            if report.error:
                status = f"failed: {report.error}"
            elif report.not_modified:
                status = "not modified"
            else:
                status = f"{report.fetched} items, {len(report.saved)} new"
            typer.echo(f"  {report.type:<15} {report.locator[:58]:<58} {status}")
            for saved in report.saved:
                typer.echo(f"    [{saved.text_policy}] {saved.title[:72]}  ({saved.reason})")


async def _ingest(topic: str | None) -> dict[str, list[SourceReport]]:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    now = datetime.now(UTC)
    try:
        await purge_expired_content(engine, now=now)
        active = await active_topic_slugs(engine)
        if topic and topic not in active:
            raise typer.BadParameter(f"no active topic {topic!r}; active: {', '.join(active)}")
        embeddings = LocalEmbeddings(settings.embedding_cache_dir)
        async with create_http() as http:
            return {
                slug: await ingest_topic(
                    engine=engine,
                    http=http,
                    embeddings=embeddings,
                    slug=slug,
                    now=now,
                    github_token=settings.github_token,
                )
                for slug in ([topic] if topic else active)
            }
    finally:
        await engine.dispose()
