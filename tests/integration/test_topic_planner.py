from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx2
import pytest
from langchain_core.embeddings import Embeddings
from langgraph.types import Command
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine

from dailyainotes.api.app import create_app
from dailyainotes.db import planner as planner_db
from dailyainotes.db.checkpoints import checkpointer
from dailyainotes.db.tables import Source, Topic, TopicProfile, TopicSource
from dailyainotes.graphs.planning import EmptyPlanError, decide_plan
from dailyainotes.graphs.topic_planner import MoreSites, PlannerDeps, ProfileDraft, build_planner
from dailyainotes.ingestion.catalog import Catalog, sync_catalog
from dailyainotes.settings import Settings

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
    """Drafts `draft`; asked for more sites, answers `more`."""

    def __init__(self, draft: ProfileDraft = DRAFT, more: list[str] | None = None) -> None:
        self.draft = draft
        self.more = more or []
        self.asked: list[tuple[str, str]] = []

    @property
    def calls(self) -> int:
        return len(self.asked)

    async def structured[T: BaseModel](
        self, role: str, schema: type[T], *, system: str, user: str, run_id: int | None = None
    ) -> T:
        self.asked.append((system, user))
        if schema is MoreSites:
            return schema.model_validate({"candidate_sites": self.more})
        return schema.model_validate(self.draft.model_dump())


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
    embeddings: Embeddings,
    web: Callable[..., Any],
    fixture: Callable[[str], bytes],
) -> None:
    router = FakeRouter()
    state, config = await start(engine)
    recorded = web(site(fixture))
    async with checkpointer(database_url) as saver:
        graph = build_planner(PlannerDeps(engine, router, recorded.http, NOW, embeddings), saver)

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

        await graph.ainvoke(
            Command(resume={"decision": "approve", "comment": "ok", "by": "dan review"}), config
        )

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
    # One readable feed is fewer than three, so the planner asked once more for sites.
    assert router.calls == 2


async def test_a_rejected_plan_leaves_the_topic_as_it_was(
    engine: AsyncEngine,
    database_url: str,
    embeddings: Embeddings,
    web: Callable[..., Any],
    fixture: Callable[[str], bytes],
) -> None:
    router = FakeRouter()
    state, config = await start(engine)
    async with checkpointer(database_url) as saver:
        graph = build_planner(
            PlannerDeps(engine, router, web(site(fixture)).http, NOW, embeddings), saver
        )
        await graph.ainvoke(state, config)

        await graph.ainvoke(
            Command(resume={"decision": "reject", "comment": "too broad", "by": "dan review"}),
            config,
        )

    async with engine.connect() as connection:
        status = (
            await connection.execute(select(Topic.status).where(Topic.slug == "demo"))
        ).scalar_one()
        sources = (await connection.execute(select(Source.id))).all()
    assert status == "draft"
    assert sources == []
    (rejected,) = await planner_db.proposals(engine, status="rejected")
    assert rejected.profile["sources"]


async def test_a_feed_whose_pages_a_model_may_not_read_is_not_proposed(
    engine: AsyncEngine,
    database_url: str,
    embeddings: Embeddings,
    web: Callable[..., Any],
    fixture: Callable[[str], bytes],
) -> None:
    """The feed is on topic, but its publisher's robots.txt blocks us, so every story from it
    would be link-only (found 2026-10-13: film and TV)."""
    blocked = {"https://news.example.com/robots.txt": b"User-agent: *\nDisallow: /\n"}
    recorded = web({**blocked, **site(fixture)})
    state, config = await start(engine)
    async with checkpointer(database_url) as saver:
        graph = build_planner(
            PlannerDeps(engine, FakeRouter(), recorded.http, NOW, embeddings), saver
        )
        await graph.ainvoke(state, config)

    (proposal,) = await planner_db.proposals(engine, status="proposed")
    kinds = [s["type"] for s in proposal.profile["sources"]]
    assert "rss" not in kinds
    assert kinds == ["arxiv", "github_releases", "hackernews"]
    # The policy gate decided from robots.txt alone: no article page was fetched.
    assert not any("/2026/10/" in str(r.url) for r in recorded.requests)


async def test_a_feed_whose_headlines_are_closest_to_the_topic_is_kept_without_keywords(
    engine: AsyncEngine,
    database_url: str,
    embeddings: Embeddings,
    web: Callable[..., Any],
    fixture: Callable[[str], bytes],
) -> None:
    """Headlines of a broad topic rarely contain its exact phrases (found 2026-10-16: Xbox Wire
    matched 10% for video games); what they are closest to still tells."""
    racing = "Motor racing: safety car, wet race, grid drop, power unit"
    await sync_catalog(
        engine,
        Catalog.model_validate(
            {
                "topics": [
                    {
                        "slug": "racing",
                        "name": "Motor racing",
                        "description": racing.split(": ")[1],
                    },
                    {"slug": "roses", "name": "Gardening", "description": "Roses, soil, pruning"},
                ]
            }
        ),
    )
    topic = await planner_db.topic(engine, "racing")
    assert topic is not None
    no_keywords = ProfileDraft(keywords=["zeppelin", "airship", "blimp"], candidate_sites=[SITE])
    thread_id = f"plan:racing:{uuid4()}"
    state = {
        "topic_id": topic.id,
        "slug": "racing",
        "name": "Motor racing",
        "description": racing.split(": ")[1],
        "version": 1,
        "thread_id": thread_id,
    }
    async with checkpointer(database_url) as saver:
        deps = PlannerDeps(
            engine, FakeRouter(no_keywords), web(site(fixture)).http, NOW, embeddings
        )
        await build_planner(deps, saver).ainvoke(state, {"configurable": {"thread_id": thread_id}})

    (proposal,) = await planner_db.proposals(engine, status="proposed")
    (feed,) = proposal.profile["sources"]
    assert feed["locator"] == f"{SITE}blog/feed.xml"
    assert feed["match_share"] == 0.0
    assert feed["topic_share"] >= 0.35


BLOCKED = "https://blocked.example.net/"
NO_FEED = "https://nofeed.example.net/"
SITES_ONLY = ProfileDraft(keywords=DRAFT.keywords, candidate_sites=[BLOCKED, NO_FEED])


def unusable() -> dict[str, Any]:
    """A site whose robots.txt blocks us, and one that advertises no feed."""
    return {
        f"{BLOCKED}robots.txt": b"User-agent: *\nDisallow: /\n",
        f"{NO_FEED}robots.txt": (404, b"", {}),
        NO_FEED: (200, b"<html><body>No feed here</body></html>", {"Content-Type": "text/html"}),
    }


async def test_too_few_readable_feeds_ask_the_model_for_other_sites_with_the_reasons(
    engine: AsyncEngine,
    database_url: str,
    embeddings: Embeddings,
    web: Callable[..., Any],
    fixture: Callable[[str], bytes],
) -> None:
    router = FakeRouter(SITES_ONLY, more=[BLOCKED, SITE])
    state, config = await start(engine)
    async with checkpointer(database_url) as saver:
        graph = build_planner(
            PlannerDeps(engine, router, web({**unusable(), **site(fixture)}).http, NOW, embeddings),
            saver,
        )
        await graph.ainvoke(state, config)

    (first_system, _), (_, second_user) = router.asked
    assert "block AI crawlers" in first_system
    assert f"- {BLOCKED}: its robots.txt disallows us" in second_user
    assert f"- {NO_FEED}: advertises no feed, nor serves one at the usual paths" in second_user
    (proposal,) = await planner_db.proposals(engine, status="proposed")
    assert [s["locator"] for s in proposal.profile["sources"]] == [f"{SITE}blog/feed.xml"]
    dropped = {d["locator"]: d["reason"] for d in proposal.profile["dropped"]}
    assert dropped[BLOCKED] == "its robots.txt disallows us"
    assert dropped[NO_FEED] == "advertises no feed, nor serves one at the usual paths"
    assert dropped[f"{SITE}atom.xml"].startswith("off topic")


async def test_the_planner_stops_after_its_second_round(
    engine: AsyncEngine,
    database_url: str,
    embeddings: Embeddings,
    web: Callable[..., Any],
) -> None:
    router = FakeRouter(SITES_ONLY, more=[NO_FEED, "https://elsewhere.example.net/"])
    state, config = await start(engine)
    async with checkpointer(database_url) as saver:
        graph = build_planner(
            PlannerDeps(engine, router, web(unusable()).http, NOW, embeddings), saver
        )
        paused = await graph.ainvoke(state, config)

    assert "__interrupt__" in paused
    assert router.calls == 2
    (proposal,) = await planner_db.proposals(engine, status="proposed")
    assert proposal.profile["sources"] == []
    assert {d["locator"] for d in proposal.profile["dropped"]} == {
        BLOCKED,
        NO_FEED,
        "https://elsewhere.example.net/",
    }


async def test_a_plan_without_sources_can_be_rejected_but_not_approved(
    engine: AsyncEngine,
    database_url: str,
    embeddings: Embeddings,
    web: Callable[..., Any],
) -> None:
    state, config = await start(engine)
    async with checkpointer(database_url) as saver:
        graph = build_planner(
            PlannerDeps(engine, FakeRouter(SITES_ONLY), web(unusable()).http, NOW, embeddings),
            saver,
        )
        await graph.ainvoke(state, config)
        (proposal,) = await planner_db.proposals(engine, status="proposed")

        with pytest.raises(EmptyPlanError):
            await decide_plan(engine, graph, proposal.id, "approve", "", by="dan review")
        await decide_plan(engine, graph, proposal.id, "reject", "nothing usable", by="dan review")

    (rejected,) = await planner_db.proposals(engine, status="rejected")
    assert rejected.id == proposal.id


async def test_the_editor_reviews_a_plan_at_admin(
    engine: AsyncEngine,
    database_url: str,
    embeddings: Embeddings,
    web: Callable[..., Any],
    fixture: Callable[[str], bytes],
    access: Any,
) -> None:
    state, config = await start(engine)
    async with checkpointer(database_url) as saver:
        graph = build_planner(
            PlannerDeps(engine, FakeRouter(), web(site(fixture)).http, NOW, embeddings), saver
        )
        await graph.ainvoke(state, config)
    app = create_app(Settings(_env_file=None, database_url=database_url))
    app.state.engine = engine  # ASGITransport does not run the lifespan
    app.state.access = access.verifier
    editor = {"Cf-Access-Jwt-Assertion": access.token("editor@example.com")}

    transport = httpx2.ASGITransport(app=app)
    async with httpx2.AsyncClient(transport=transport, base_url="http://test") as client:
        (plan,) = (await client.get("/api/v1/admin/plans", headers=editor)).json()
        approved = await client.post(
            f"/api/v1/admin/plans/{plan['id']}/decision",
            json={"decision": "approve", "comment": "good feeds"},
            headers=editor,
        )
        again = await client.post(
            f"/api/v1/admin/plans/{plan['id']}/decision",
            json={"decision": "reject"},
            headers=editor,
        )
        left = (await client.get("/api/v1/admin/plans", headers=editor)).json()

    assert (plan["topic"], plan["name"], plan["version"]) == ("demo", "Demo", 1)
    assert plan["keywords"] == ["safety car", "engine penalty", "grid"]
    (feed,) = [s for s in plan["sources"] if s["type"] == "rss"]
    assert feed["readable_share"] == 1.0
    dropped = {d["locator"]: d["reason"] for d in plan["dropped"]}
    assert dropped["http://insecure.example.com/"] == "not an https address"
    assert dropped[GUARDIAN] == "an excluded publisher"
    assert approved.json() == {"status": "approved"}
    assert again.status_code == 409
    assert left == []
    async with engine.connect() as connection:
        status = (
            await connection.execute(select(Topic.status).where(Topic.slug == "demo"))
        ).scalar_one()
        decided = (await connection.execute(select(TopicProfile.decided_by))).scalar_one()
    assert (status, decided) == ("active", "editor@example.com")
