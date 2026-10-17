"""Running the Topic Planner for one topic, and resuming it with the editor's decision. `dan
topics plan`, `dan review`, the worker and /admin all come here."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from langchain_core.embeddings import Embeddings
from langgraph.types import Command

from dailyainotes.db import planner as db
from dailyainotes.db.checkpoints import checkpointer
from dailyainotes.db.engine import AsyncEngine
from dailyainotes.db.runs import DbLedger, finish_run, finish_waiting_runs, start_run
from dailyainotes.graphs.topic_planner import PlannerDeps, build_planner
from dailyainotes.llm.providers import build_router
from dailyainotes.llm.router import ModelsExhaustedError
from dailyainotes.llm.tracing import flush_tracing
from dailyainotes.settings import Settings
from dailyainotes.sources.http import create_http


class UnknownTopicError(Exception):
    pass


class NotProposedError(Exception):
    """The plan was already approved or rejected, or does not exist."""


class EmptyPlanError(Exception):
    """The plan keeps no source: approving it would make a topic active with nothing to read."""


@asynccontextmanager
async def planner(
    settings: Settings, engine: AsyncEngine, embeddings: Embeddings | None = None
) -> AsyncIterator[Any]:
    """The Topic Planner graph with its models, HTTP client and checkpointer. Planning needs
    `embeddings`; resuming a plan with the editor's decision does not."""
    router = build_router(settings, DbLedger(engine))
    try:
        async with create_http() as http, checkpointer(settings.database_url) as saver:
            deps = PlannerDeps(engine, router, http, datetime.now(UTC), embeddings)
            yield build_planner(deps, saver)
    finally:
        flush_tracing(settings)


async def plan_topic(engine: AsyncEngine, graph: Any, slug: str) -> db.Proposal:
    """Run the planner until its proposal waits for the editor."""
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
    await finish_run(engine, run_id, "waiting")
    (proposal,) = [p for p in await db.proposals(engine) if p.thread_id == thread_id]
    return proposal


async def decide_plan(
    engine: AsyncEngine, graph: Any, proposal_id: int, decision: str, comment: str, *, by: str
) -> None:
    """Resume the plan's paused graph: approving adds its sources and activates the topic."""
    proposal = await db.proposal(engine, proposal_id)
    if proposal is None or proposal.status != "proposed":
        status = proposal.status if proposal else "missing"
        raise NotProposedError(f"plan-{proposal_id} is {status}, not waiting for review")
    if decision == "approve" and not proposal.profile["sources"]:
        raise EmptyPlanError(
            f"plan-{proposal_id} has no sources: reject it, or plan the topic again"
        )
    resume: Command[Any] = Command(resume={"decision": decision, "comment": comment, "by": by})
    await graph.ainvoke(resume, {"configurable": {"thread_id": proposal.thread_id}})
    await finish_waiting_runs(engine, proposal.thread_id, "done")
