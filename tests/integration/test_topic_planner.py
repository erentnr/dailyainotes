from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from langgraph.types import Command
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine

from dailyainotes.db import planner as planner_db
from dailyainotes.db.checkpoints import checkpointer
from dailyainotes.db.tables import Source, Topic, TopicSource
from dailyainotes.graphs.topic_planner import PlannerDeps, ProfileDraft, build_planner
from dailyainotes.ingestion.catalog import Catalog, sync_catalog

pytestmark = [pytest.mark.integration, pytest.mark.anyio]

NOW = datetime(2026, 10, 12, 18, tzinfo=UTC)
SITE = "https://lab.example.org/"
# Excluded by INTENT.md: never fetched, never proposed.
GUARDIAN = "https://www.theguardian.com/science/space"
DRAFT = ProfileDraft(
    keywords=["safety car", "engine penalty", "grid"],
    entities=[],
    candidate_sites=[SITE, "http://insecure.example.com/", GUARDIAN],
    arxiv_query='abs:"open-weight"',
    github_repos=["vllm-project/vllm"],
    hackernews_query="open weights",
)


class FakeRouter:
    def __init__(self) -> None:
        self.calls = 0

    async def structured[T: BaseModel](
        self, role: str, schema: type[T], *, system: str, user: str, run_id: int | None = None
    ) -> T:
        self.calls += 1
        return schema.model_validate(DRAFT.model_dump())


def site(fixture: Callable[[str], bytes]) -> dict[str, Any]:
    html = {"Content-Type": "text/html"}
    # Most specific first: the site's own prefix would match every URL under it.
    return {
        f"{SITE}robots.txt": (404, b"", {}),
        "https://www.theguardian.com/robots.txt": (404, b"", {}),
        "https://www.theguardian.com/blog/feed.xml": fixture("rss/feed.xml"),
        GUARDIAN: (200, fixture("rss/homepage.html"), html),
        f"{SITE}blog/feed.xml": fixture("rss/feed.xml"),
        f"{SITE}atom.xml": fixture("rss/atom.xml"),
        SITE: (200, fixture("rss/homepage.html"), html),
        "https://export.arxiv.org/api/query": fixture("arxiv/query.xml"),
        "https://api.github.com/repos/": fixture("github/releases.json"),
        "https://hn.algolia.com/": fixture("hackernews/search.json"),
    }


async def start(engine: AsyncEngine) -> tuple[dict[str, Any], dict[str, Any]]:
    """A draft topic, and the planner's first state and thread config for it."""
    await sync_catalog(
        engine,
        Catalog.model_validate({"topics": [{"slug": "demo", "name": "Demo", "description": "d"}]}),
    )
    topic = await planner_db.topic(engine, "demo")
    assert topic is not None
    thread_id = f"plan:demo:{uuid4()}"
    state = {
        "topic_id": topic.id,
        "slug": "demo",
        "name": "Demo",
        "description": "d",
        "version": 1,
        "thread_id": thread_id,
    }
    return state, {"configurable": {"thread_id": thread_id}}


async def test_a_plan_waits_for_approval_then_activates_the_topic(
    engine: AsyncEngine,
    database_url: str,
    web: Callable[..., Any],
    fixture: Callable[[str], bytes],
) -> None:
    router = FakeRouter()
    state, config = await start(engine)
    recorded = web(site(fixture))
    async with checkpointer(database_url) as saver:
        graph = build_planner(PlannerDeps(engine, router, recorded.http, NOW), saver)

        paused = await graph.ainvoke(state, config)

        assert "__interrupt__" in paused
        (proposal,) = await planner_db.proposals(engine, status="proposed")
        assert proposal.profile["keywords"] == ["safety car", "engine penalty", "grid"]
        sources = {(s["type"], s["locator"]) for s in proposal.profile["sources"]}
        assert sources == {
            ("rss", f"{SITE}blog/feed.xml"),
            ("arxiv", 'abs:"open-weight"'),
            ("github_releases", "vllm-project/vllm"),
            ("hackernews", "open weights"),
        }
        assert not any("insecure" in str(r.url) for r in recorded.requests)
        assert not any("theguardian" in str(r.url) for r in recorded.requests)

        await graph.ainvoke(Command(resume={"decision": "approve", "comment": "ok"}), config)

    async with engine.connect() as connection:
        status = (
            await connection.execute(select(Topic.status).where(Topic.slug == "demo"))
        ).scalar_one()
        linked = (
            await connection.execute(
                select(Source.locator)
                .join(TopicSource, TopicSource.source_id == Source.id)
                .join(Topic, Topic.id == TopicSource.topic_id)
                .where(Topic.slug == "demo")
            )
        ).scalars()
        assert status == "active"
        assert set(linked) == {locator for _, locator in sources}
    (approved,) = await planner_db.proposals(engine, status="approved")
    assert approved.id == proposal.id
    assert router.calls == 1


async def test_a_rejected_plan_leaves_the_topic_as_it_was(
    engine: AsyncEngine,
    database_url: str,
    web: Callable[..., Any],
    fixture: Callable[[str], bytes],
) -> None:
    router = FakeRouter()
    state, config = await start(engine)
    async with checkpointer(database_url) as saver:
        graph = build_planner(PlannerDeps(engine, router, web(site(fixture)).http, NOW), saver)
        await graph.ainvoke(state, config)

        await graph.ainvoke(Command(resume={"decision": "reject", "comment": "too broad"}), config)

    async with engine.connect() as connection:
        status = (
            await connection.execute(select(Topic.status).where(Topic.slug == "demo"))
        ).scalar_one()
        sources = (await connection.execute(select(Source.id))).all()
    assert status == "draft"
    assert sources == []
    (rejected,) = await planner_db.proposals(engine, status="rejected")
    assert rejected.profile["sources"]
