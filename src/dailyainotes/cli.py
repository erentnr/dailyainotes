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
from dailyainotes.retrieval.hybrid import SearchHit, hybrid_search
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


@app.command()
def search(
    query: str,
    topic: Annotated[list[str] | None, typer.Option(help="Limit to a topic slug.")] = None,
    limit: Annotated[int, typer.Option(help="How many results.")] = 8,
    explain: Annotated[bool, typer.Option(help="Show each method's rank.")] = False,
) -> None:
    """Hybrid search over ingested sources: full text and vectors, fused."""
    hits = asyncio.run(_search(query, topic, limit))
    if not hits:
        typer.echo("No results.")
    for position, hit in enumerate(hits, start=1):
        chunk = hit.chunk
        date = chunk.published_at.date().isoformat() if chunk.published_at else "undated"
        typer.echo(f"{position}. {chunk.title}")
        typer.echo(
            f"   {chunk.publisher or 'unknown'} · {date} · {chunk.text_policy} · {chunk.url}"
        )
        if explain:
            ranks = f"full text #{hit.full_text_rank or '-'} · vector #{hit.vector_rank or '-'}"
            typer.echo(f"   fused {hit.score:.4f} = {ranks} · chunk {chunk.ordinal}")
            typer.echo(f"   {' '.join(chunk.text.split())[:160]}")


async def _search(query: str, topics: list[str] | None, limit: int) -> list[SearchHit]:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    try:
        embeddings = LocalEmbeddings(settings.embedding_cache_dir)
        return await hybrid_search(engine, embeddings, query, topic_slugs=topics, limit=limit)
    finally:
        await engine.dispose()
