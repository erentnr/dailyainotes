"""Running the Topic Planner for one topic: `dan topics plan` and the worker come here. The plan
decides itself (ADR 0008)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from langchain_core.embeddings import Embeddings

from dailyainotes.db import planner as db
from dailyainotes.db.checkpoints import checkpointer
from dailyainotes.db.engine import AsyncEngine
from dailyainotes.db.runs import DbLedger, finish_run, start_run
from dailyainotes.graphs.topic_planner import PlannerDeps, build_planner
from dailyainotes.llm.providers import build_router
from dailyainotes.llm.router import ModelsExhaustedError
from dailyainotes.llm.tracing import flush_tracing
from dailyainotes.settings import Settings
from dailyainotes.sources.http import create_http


class UnknownTopicError(Exception):
    pass


@asynccontextmanager
async def planner(
    settings: Settings, engine: AsyncEngine, embeddings: Embeddings
) -> AsyncIterator[Any]:
    """The Topic Planner graph with its models, HTTP client and checkpointer."""
    router = build_router(settings, DbLedger(engine))
    try:
        async with create_http() as http, checkpointer(settings.database_url) as saver:
            deps = PlannerDeps(engine, router, http, datetime.now(UTC), embeddings)
            yield build_planner(deps, saver)
    finally:
        flush_tracing(settings)


async def plan_topic(engine: AsyncEngine, graph: Any, slug: str) -> db.Proposal:
    """Run the planner to the end; the proposal comes back approved, with the topic live, or
    rejected with the reason."""
    topic = await db.topic(engine, slug)
    if topic is None:
        raise UnknownTopicError(f"no topic {slug!r}")
    version = await db.next_version(engine, topic.id)
    thread_id = f"plan:{topic.slug}:{version}"
    run_id = await start_run(engine, "plan", topic_id=topic.id, thread_id=thread_id)
    state = {
        "topic_id": topic.id,
        "slug": topic.slug,
        "name": topic.name,
        "description": topic.description,
        "version": version,
        "thread_id": thread_id,
        "run_id": run_id,
    }
    try:
        await graph.ainvoke(state, {"configurable": {"thread_id": thread_id}})
    except ModelsExhaustedError as error:
        await finish_run(engine, run_id, "failed", str(error))
        raise
    await finish_run(engine, run_id, "done")
    (proposal,) = [p for p in await db.proposals(engine) if p.thread_id == thread_id]
    return proposal
