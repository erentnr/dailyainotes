"""`dan`, the command line for operators and demos."""

import asyncio
import json
import time
from datetime import UTC, datetime
from importlib.metadata import version as package_version
from pathlib import Path
from typing import Annotated, Any

import typer
from pydantic import BaseModel

from dailyainotes.ask import AskDeps, ask
from dailyainotes.db import editorial as editorial_db
from dailyainotes.db import planner as planner_db
from dailyainotes.db.catalog import SyncCounts
from dailyainotes.db.engine import AsyncEngine, create_engine
from dailyainotes.db.ingest import active_topic_slugs, purge_expired_content
from dailyainotes.db.migrate import upgrade_to_head
from dailyainotes.db.runs import DbLedger
from dailyainotes.evals import EVALS, baseline, regressions, run_eval
from dailyainotes.graphs.edition import EditionReport, NoActiveTopicError, run_editions
from dailyainotes.graphs.planning import UnknownTopicError, plan_topic, planner
from dailyainotes.ingestion.catalog import CATALOG_PATH, load_catalog, sync_catalog
from dailyainotes.ingestion.run import SourceReport, ingest_topic
from dailyainotes.llm.embeddings import LocalEmbeddings
from dailyainotes.llm.providers import build_router, model_factory
from dailyainotes.llm.router import ModelsExhaustedError, Router, parse_chain
from dailyainotes.llm.tracing import flush_tracing
from dailyainotes.logging import configure_logging
from dailyainotes.retrieval.hybrid import SearchHit, hybrid_search
from dailyainotes.settings import get_settings
from dailyainotes.sources.http import create_http

app = typer.Typer(no_args_is_help=True, help="Daily AI Notes command line.")
db_app = typer.Typer(no_args_is_help=True, help="Database commands.")
catalog_app = typer.Typer(no_args_is_help=True, help="The topic catalog.")
topics_app = typer.Typer(no_args_is_help=True, help="Topic planning.")
edition_app = typer.Typer(no_args_is_help=True, help="Daily editions.")
review_app = typer.Typer(
    no_args_is_help=True, help="Read a note or a topic plan, or withdraw a published note."
)
# Recorded as who withdrew a note; /admin records the editor's email instead.
BY = "dan review"
llm_app = typer.Typer(no_args_is_help=True, help="Model providers.")
evals_app = typer.Typer(no_args_is_help=True, help="The eval set in evals/.")
app.add_typer(db_app, name="db")
app.add_typer(catalog_app, name="catalog")
app.add_typer(topics_app, name="topics")
app.add_typer(edition_app, name="edition")
app.add_typer(review_app, name="review")
app.add_typer(llm_app, name="llm")
app.add_typer(evals_app, name="evals")


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


@topics_app.command("plan")
def topics_plan(
    slug: Annotated[str | None, typer.Argument(help="A topic slug.")] = None,
    all_drafts: Annotated[bool, typer.Option("--all", help="Every topic still in draft.")] = False,
) -> None:
    """Run the Topic Planner; a plan with enough readable feeds makes the topic live."""
    if not slug and not all_drafts:
        raise typer.BadParameter("give a topic slug or --all")
    asyncio.run(_plan(slug, all_drafts))


async def _plan(slug: str | None, all_drafts: bool) -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    try:
        embeddings = LocalEmbeddings(settings.embedding_cache_dir)
        async with planner(settings, engine, embeddings) as graph:
            slugs = await planner_db.draft_topic_slugs(engine) if all_drafts else [slug or ""]
            for each in slugs:
                try:
                    proposal = await plan_topic(engine, graph, each)
                except UnknownTopicError as error:
                    raise typer.BadParameter(str(error)) from error
                except ModelsExhaustedError as error:
                    typer.echo(f"{each}: no model answered. {error}")
                    continue
                live = "; the topic is live" if proposal.status == "approved" else ""
                typer.echo(f"{each}: plan-{proposal.id} {proposal.status}{live}")
                print_proposal(proposal)
    finally:
        await engine.dispose()


def print_proposal(proposal: planner_db.Proposal) -> None:
    profile = proposal.profile
    typer.echo(f"  keywords: {', '.join(profile['keywords'])}")
    if profile["negative_keywords"]:
        typer.echo(f"  excluded: {', '.join(profile['negative_keywords'])}")
    if profile["entities"]:
        typer.echo(f"  entities: {', '.join(profile['entities'])}")
    typer.echo(f"  sources ({len(profile['sources'])}):")
    for source in profile["sources"]:
        stats = f"{source['recent_items']} recent, {source['match_share']:.0%} keywords"
        if "topic_share" in source:
            stats += f", {source['topic_share']:.0%} closest"
        typer.echo(f"    {source['type']:<15} {source['locator'][:60]:<60} {stats}")
    if dropped := profile.get("dropped", []):
        typer.echo(f"  not used ({len(dropped)}):")
        for item in dropped:
            typer.echo(f"    {item['locator'][:60]:<60} {item['reason']}")


@edition_app.command("run")
def edition_run(
    slug: Annotated[str | None, typer.Argument(help="A topic slug.")] = None,
    all_active: Annotated[bool, typer.Option("--all", help="Every active topic.")] = False,
    collect: Annotated[bool, typer.Option(help="Fetch new items first.")] = True,
) -> None:
    """Write and publish today's notes: Scout picks the stories, and each note is published
    when its checks finish."""
    if not slug and not all_active:
        raise typer.BadParameter("give a topic slug or --all")
    for report in asyncio.run(_edition(slug, collect)):
        if report.status == "skipped":
            typer.echo(f"{report.slug}: today's edition is already done")
            continue
        typer.echo(
            f"{report.slug}: {report.collected} new items, {report.stories} stories, "
            f"{len(report.published)} notes published"
        )
        for note_id in report.published:
            typer.echo(f"  note-{note_id}")
        for error in report.errors:
            typer.echo(f"  failed: {error}")


async def _edition(slug: str | None, collect: bool) -> list[EditionReport]:
    try:
        return await run_editions(get_settings(), slug, collect=collect)
    except NoActiveTopicError as error:
        raise typer.BadParameter(str(error)) from error


@review_app.command("show")
def review_show(item: str) -> None:
    """One item in full, e.g. `plan-3` or `note-12`."""
    kind, number = parse_item(item)
    if kind == "plan":
        proposal = asyncio.run(_proposal(number))
        typer.echo(f"{item} · {proposal.slug} v{proposal.version} · {proposal.status}")
        print_proposal(proposal)
        return
    note, (version, citations, claims) = asyncio.run(_note_detail(number))
    typer.echo(f"{item} · {note.topic} · {note.edition_date} · {note.status} · v{note.version}")
    typer.echo(f"\n{version.title}\n\n{version.body}\n\nWhy it matters: {version.why_it_matters}")
    typer.echo("\nSources:")
    for citation in citations:
        date = citation.published_at.date().isoformat() if citation.published_at else "undated"
        typer.echo(f"  [{citation.marker}] {citation.publisher} · {date} · {citation.url}")
    typer.echo(f"\nClaims ({note.supported}/{note.claims} supported):")
    for claim in claims:
        cites = "".join(f"[{m}]" for m in claim.markers)
        origins = (
            f"{claim.independent_origins} origin{'s' if claim.independent_origins != 1 else ''}"
        )
        typer.echo(f"  {claim.verdict:<12} {origins:<10} {claim.text} {cites}")
        if claim.verdict != "supported":
            typer.echo(f"  {'':<23} {claim.rationale}")


def parse_item(item: str) -> tuple[str, int]:
    kind, _, number = item.partition("-")
    if kind not in ("plan", "note") or not number.isdigit():
        raise typer.BadParameter(f"{item!r} is not a review item like plan-3 or note-12")
    return kind, int(number)


async def _proposal(proposal_id: int) -> planner_db.Proposal:
    engine = create_engine(get_settings().database_url)
    try:
        for proposal in await planner_db.proposals(engine):
            if proposal.id == proposal_id:
                return proposal
    finally:
        await engine.dispose()
    raise typer.BadParameter(f"no plan-{proposal_id}")


async def _note(engine: AsyncEngine, note_id: int) -> editorial_db.NoteSummary:
    for note in await editorial_db.notes(engine):
        if note.id == note_id:
            return note
    raise typer.BadParameter(f"no note-{note_id}")


async def _note_detail(note_id: int) -> tuple[editorial_db.NoteSummary, Any]:
    engine = create_engine(get_settings().database_url)
    try:
        note = await _note(engine, note_id)
        return note, await editorial_db.version_detail(engine, note.id, note.version)
    finally:
        await engine.dispose()


@review_app.command("withdraw")
def review_withdraw(
    item: str, comment: Annotated[str, typer.Option(help="Why; kept with the decision.")] = ""
) -> None:
    """Take a published note off the site, Ask and the MCP server."""
    kind, number = parse_item(item)
    if kind != "note":
        raise typer.BadParameter("only a note can be withdrawn, like note-12")
    if not asyncio.run(_withdraw(number, comment)):
        raise typer.BadParameter(f"{item} is not published")
    typer.echo(f"{item} withdrawn.")


async def _withdraw(note_id: int, comment: str) -> bool:
    engine = create_engine(get_settings().database_url)
    try:
        return await editorial_db.withdraw(engine, note_id, comment, BY)
    finally:
        await engine.dispose()


@app.command("ask")
def ask_command(
    question: str,
    topic: Annotated[list[str] | None, typer.Option(help="Limit to a topic slug.")] = None,
) -> None:
    """Ask the published notes; the answer cites them, or says they don't cover it."""
    asyncio.run(_ask(question, topic or []))


async def _ask(question: str, topics: list[str]) -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    try:
        embeddings = LocalEmbeddings(settings.embedding_cache_dir)
        deps = AskDeps(engine, embeddings, build_router(settings, DbLedger(engine)))
        sources: list[dict[str, Any]] = []
        async for kind, data in ask(deps, question, topics):
            if kind == "sources":
                sources = data
            elif kind == "text":
                typer.echo(data, nl=False)
            elif kind == "error":
                typer.echo(data, err=True)
            elif kind == "done":
                typer.echo()
                for marker in data["cited"]:
                    s = sources[marker - 1]
                    typer.echo(f"[{marker}] {s['title']} · {s['topic']} · {s['edition_date']}")
    finally:
        flush_tracing(settings)
        await engine.dispose()


@evals_app.command("run")
def evals_run(
    judge: Annotated[
        bool, typer.Option(help="Also answer with the Ask model and have the judge check it.")
    ] = False,
    record: Annotated[bool, typer.Option(help="Save the scores in eval_runs.")] = False,
    update_baseline: Annotated[
        bool, typer.Option(help="Write these scores to evals/baseline.json.")
    ] = False,
) -> None:
    """Score Ask on the 30 questions; fails when a score falls below the baseline."""
    metrics, results = asyncio.run(run_eval(get_settings(), judge=judge, record=record))
    for r in results:
        if r.expected:
            outcome = f"#{r.rank}" if r.rank else "missed"
        else:
            outcome = "not enough" if not r.sources else f"{len(r.sources)} sources"
        faithful = {True: "  faithful", False: "  NOT faithful", None: ""}[r.faithful]
        typer.echo(f"{r.id:>2}  {outcome:<10}  {r.question}{faithful}")
    typer.echo(json.dumps(metrics, indent=2))
    if update_baseline:
        kept = {k: v for k, v in metrics.items() if k not in ("questions", "faithfulness")}
        (EVALS / "baseline.json").write_text(json.dumps(kept, indent=2) + "\n")
        typer.echo("evals/baseline.json updated; say why in the commit message.")
        return
    if failed := regressions(metrics, baseline()):
        typer.echo("Below the baseline: " + "; ".join(failed), err=True)
        raise typer.Exit(1)


class ProbeAnswer(BaseModel):
    answer: int


@llm_app.command("probe")
def llm_probe() -> None:
    """Ask every configured model a tiny question; show what works, and how."""
    asyncio.run(_probe())


async def _probe() -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    make_model = model_factory(settings)
    chains = [
        settings.llm_planner,
        settings.llm_researcher,
        settings.llm_writer,
        settings.llm_extractor,
        settings.llm_verifier,
        settings.llm_ask,
        settings.llm_judge,
    ]
    refs = dict.fromkeys(ref for chain in chains for ref in parse_chain(chain))
    try:
        for ref in refs:
            router = Router({"probe": [ref]}, make_model, DbLedger(engine))
            started = time.monotonic()
            try:
                await router.structured("probe", ProbeAnswer, system="Answer.", user="2 + 2?")
                prompt_json = f"ok in {time.monotonic() - started:.1f}s"
            except ModelsExhaustedError as error:
                prompt_json = f"failed ({'; '.join(error.attempts)})"
            try:
                native = make_model(ref).with_structured_output(ProbeAnswer, method="json_schema")
                await native.ainvoke("What is 2 + 2?")
                native_json = "supported"
            except Exception as error:
                native_json = f"no ({type(error).__name__})"
            typer.echo(
                f"{ref}\n  JSON in the prompt: {prompt_json}\n  native JSON schema: {native_json}"
            )
    finally:
        await engine.dispose()
