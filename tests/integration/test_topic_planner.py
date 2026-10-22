from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from langchain_core.embeddings import Embeddings
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine

from dailyainotes import accounts
from dailyainotes.db import planner as planner_db
from dailyainotes.db import suggestions as suggestions_db
from dailyainotes.db.checkpoints import checkpointer
from dailyainotes.db.tables import Source, Topic, TopicProfile, TopicSource
from dailyainotes.graphs import topic_planner
from dailyainotes.graphs.topic_planner import MoreSites, PlannerDeps, ProfileDraft, build_planner
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


async def test_a_plan_with_enough_readable_feeds_makes_the_topic_live(
    engine: AsyncEngine,
    database_url: str,
    embeddings: Embeddings,
    web: Callable[..., Any],
    fixture: Callable[[str], bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The fixture site has one readable, on-topic feed.
    monkeypatch.setattr(topic_planner, "MIN_FEEDS", 1)
    router = FakeRouter()
    state, config = await start(engine)
    recorded = web(site(fixture))
    async with checkpointer(database_url) as saver:
        graph = build_planner(PlannerDeps(engine, router, recorded.http, NOW, embeddings), saver)

        finished = await graph.ainvoke(state, config)

    assert "__interrupt__" not in finished
    (proposal,) = await planner_db.proposals(engine)
    assert proposal.status == "approved"
    assert proposal.profile["keywords"] == ["safety car", "engine penalty", "grid"]
    sources = {(s["type"], s["locator"]) for s in proposal.profile["sources"]}
    assert sources == {
        ("rss", f"{SITE}blog/feed.xml"),
        ("arxiv", 'abs:"open-weight"'),
        ("github_releases", "vllm-project/vllm"),
        ("hackernews", "open weights"),
    }
    (feed,) = [s for s in proposal.profile["sources"] if s["type"] == "rss"]
    assert feed["readable_share"] == 1.0
    dropped = {d["locator"]: d["reason"] for d in proposal.profile["dropped"]}
    assert dropped["http://insecure.example.com/"] == "not an https address"
    assert dropped[GUARDIAN] == "an excluded publisher"
    assert not any("insecure" in str(r.url) for r in recorded.requests)
    assert not any("theguardian" in str(r.url) for r in recorded.requests)
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
        decided = (await connection.execute(select(TopicProfile.decided_by))).scalar_one()
        assert status == "active"
        assert set(linked) == {locator for _, locator in sources}
    assert decided == "automatic"
    # One feed is enough here, so the planner did not ask for more sites.
    assert router.calls == 1


async def test_a_plan_with_too_few_readable_feeds_is_rejected_and_the_topic_stays_a_draft(
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

    async with engine.connect() as connection:
        status = (
            await connection.execute(select(Topic.status).where(Topic.slug == "demo"))
        ).scalar_one()
        sources = (await connection.execute(select(Source.id))).all()
        comment, decided = (
            await connection.execute(select(TopicProfile.decision_comment, TopicProfile.decided_by))
        ).one()
    assert (status, sources) == ("draft", [])
    (rejected,) = await planner_db.proposals(engine, status="rejected")
    assert rejected.profile["sources"]
    assert comment == "We found 1 news feed we may read on this topic; it needs 3."
    assert decided == "automatic"
    # One readable feed is fewer than three, so the planner asked once more for sites.
    assert router.calls == 2


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

    (proposal,) = await planner_db.proposals(engine)
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

    (proposal,) = await planner_db.proposals(engine)
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
    (proposal,) = await planner_db.proposals(engine)
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
        await graph.ainvoke(state, config)

    assert router.calls == 2
    (proposal,) = await planner_db.proposals(engine)
    assert (proposal.status, proposal.profile["sources"]) == ("rejected", [])
    assert {d["locator"] for d in proposal.profile["dropped"]} == {
        BLOCKED,
        NO_FEED,
        "https://elsewhere.example.net/",
    }


async def reader_adds_chess(
    engine: AsyncEngine,
    database_url: str,
    embeddings: Embeddings,
    web: Callable[..., Any],
    fixture: Callable[[str], bytes],
) -> int:
    """A reader who follows topics in slots 1 and 2 adds "Chess", and the Topic Planner plans it
    and decides: the reader's id."""
    await sync_catalog(
        engine,
        Catalog.model_validate(
            {
                "topics": [
                    {"slug": slug, "name": slug.title(), "description": "d", "sources": [feed]}
                    for slug, feed in (
                        ("demo", {"type": "rss", "url": "https://x.example/feed"}),
                        ("other", {"type": "rss", "url": "https://y.example/feed"}),
                    )
                ]
            }
        ),
    )
    session = await accounts.open_session(engine, "reader@example.com", datetime.now(UTC))
    await accounts.follow(
        engine, session.reader_id, [accounts.Followed("demo", 1), accounts.Followed("other", 2)]
    )
    slug = await suggestions_db.add(engine, session.reader_id, "Chess", "")
    topic = await planner_db.topic(engine, slug)
    assert topic is not None
    thread_id = f"plan:{slug}:{uuid4()}"
    state = {"topic_id": topic.id, "slug": slug, "name": "Chess", "description": "Chess"}
    async with checkpointer(database_url) as saver:
        deps = PlannerDeps(engine, FakeRouter(), web(site(fixture)).http, NOW, embeddings)
        await build_planner(deps, saver).ainvoke(
            {**state, "version": 1, "thread_id": thread_id},
            {"configurable": {"thread_id": thread_id}},
        )
    return session.reader_id


async def test_a_topic_a_reader_added_joins_their_topics_when_it_goes_live(
    engine: AsyncEngine,
    database_url: str,
    embeddings: Embeddings,
    web: Callable[..., Any],
    fixture: Callable[[str], bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(topic_planner, "MIN_FEEDS", 1)

    reader_id = await reader_adds_chess(engine, database_url, embeddings, web, fixture)

    topics = await accounts.followed(engine, reader_id)
    assert sorted((t.slug, t.slot) for t in topics) == [("chess", 3), ("demo", 1), ("other", 2)]
    (mine,) = await accounts.suggestions(engine, reader_id)
    assert (mine.status, mine.topic_status) == ("accepted", "active")


async def test_a_rejected_plan_tells_the_reader_who_added_the_topic_why(
    engine: AsyncEngine,
    database_url: str,
    embeddings: Embeddings,
    web: Callable[..., Any],
    fixture: Callable[[str], bytes],
) -> None:
    reader_id = await reader_adds_chess(engine, database_url, embeddings, web, fixture)

    (mine,) = await accounts.suggestions(engine, reader_id)
    assert (mine.status, mine.reason) == (
        "declined",
        "We found 1 news feed we may read on this topic; it needs 3.",
    )
    assert sorted(t.slug for t in await accounts.followed(engine, reader_id)) == ["demo", "other"]
