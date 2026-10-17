from collections import Counter, defaultdict
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import anyio
import httpx2
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from langchain_core.embeddings import Embeddings
from langgraph.types import Command
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine
from typer.testing import CliRunner

from dailyainotes.api.app import create_app
from dailyainotes.api.deps import story_deps
from dailyainotes.cli import app
from dailyainotes.db import editorial as db
from dailyainotes.db.checkpoints import checkpointer
from dailyainotes.db.ingest import NewDocument, save_document
from dailyainotes.db.tables import (
    Approval,
    Document,
    Note,
    Publisher,
    Source,
    Story,
    StoryDocument,
    Topic,
)
from dailyainotes.domain.chunking import heading_chunk
from dailyainotes.graphs import scout as scout_graph
from dailyainotes.graphs.edition import decide_note, run_edition
from dailyainotes.graphs.scout import Relevance, ScoutDeps, build_scout
from dailyainotes.graphs.story import (
    Brief,
    Claims,
    ClaimVerdict,
    Disagreement,
    Draft,
    ExtractedClaim,
    Position,
    StoryDeps,
    Verdicts,
    build_story_graph,
)
from dailyainotes.ingestion.catalog import Catalog, sync_catalog
from dailyainotes.llm.router import ModelsExhaustedError
from dailyainotes.settings import Settings
from dailyainotes.sources.urls import url_hash

pytestmark = [pytest.mark.integration, pytest.mark.anyio]

NOW = datetime(2026, 10, 13, 12, tzinfo=UTC)
WIN = (
    "Max Verstappen won the United States Grand Prix in Austin by 4.2 seconds from pole "
    "position, extending his lead in the championship."
)
KINDS = {
    "fia.example.com": "primary",
    "wire.example.com": "wire",
    "blog.example.org": "specialist",
    "paper.example.net": "editorial",
}
# Publisher, title, lead and text policy. The first three are one story.
REPORTS = [
    ("fia.example.com", "Verstappen wins the United States Grand Prix", WIN, "full"),
    ("wire.example.com", "Verstappen wins the United States Grand Prix in Austin", WIN, "summary"),
    ("blog.example.org", "Verstappen wins the United States Grand Prix", WIN, "summary"),
    (
        "blog.example.org",
        "Pirelli brings its softest tyres to Mexico City",
        "The supplier picked its three softest compounds for the high-altitude race.",
        "summary",
    ),
    (
        "paper.example.net",
        "Team principal leaves after ten years in charge",
        "The departure was announced on Monday morning.",
        "link_only",
    ),
]

BRIEF = Brief(key_facts=[], angle="Verstappen won in Austin.")
PLANTED = Draft(
    title="Verstappen wins in Austin",
    body="Max Verstappen won the United States Grand Prix by 5.1 seconds [1][2].",
    why_it_matters="The win extends his lead in the championship [2][3].",
)
CORRECT = Draft(
    title="Verstappen wins in Austin",
    body=(
        "Max Verstappen won the United States Grand Prix in Austin by 4.2 seconds [1][2]. "
        "He started from pole position [1][2]."
    ),
    why_it_matters="The win extends his lead in the championship [2][3].",
)
CLAIMS = Claims(
    claims=[
        ExtractedClaim(text="Verstappen won by 4.2 seconds", kind="numeric", markers=[1, 2]),
        ExtractedClaim(text="He started from pole position", kind="factual", markers=[1, 2]),
        ExtractedClaim(text="The win extends his lead", kind="factual", markers=[2, 3]),
    ]
)


def verdicts(*supporting: list[int]) -> Verdicts:
    return Verdicts(
        verdicts=[
            ClaimVerdict(claim=i, verdict="supported", supporting=s, rationale="Stated.")
            for i, s in enumerate(supporting, start=1)
        ]
    )


# Fits any story: one claim, attributed to evidence 1.
ANY_STORY: dict[str, list[BaseModel | Exception]] = {
    "researcher": [Brief(key_facts=[], angle="The event.")],
    "writer": [
        Draft(
            title="Event",
            body="The publisher reports it [1].",
            why_it_matters="Fans follow it [1].",
        )
    ],
    "extractor": [
        Claims(
            claims=[ExtractedClaim(text="The publisher reports it", kind="attributed", markers=[1])]
        )
    ],
    "verifier": [verdicts([1])],
}


class ScriptedRouter:
    """Answers each role from its script in order; the last answer repeats."""

    def __init__(self, script: dict[str, list[BaseModel | Exception]]) -> None:
        self.script = script
        self.calls: Counter[str] = Counter()
        self.prompts: dict[str, list[str]] = defaultdict(list)

    async def structured[T: BaseModel](
        self, role: str, schema: type[T], *, system: str, user: str, run_id: int | None = None
    ) -> T:
        answers = self.script[role]
        answer = answers[min(self.calls[role], len(answers) - 1)]
        self.calls[role] += 1
        self.prompts[role].append(user)
        if isinstance(answer, Exception):
            raise answer
        return schema.model_validate(answer.model_dump())


async def seed(engine: AsyncEngine, embeddings: Embeddings) -> int:
    """The catalog topic `f1` with one feed per publisher and the reports above; its id."""
    await sync_catalog(
        engine,
        Catalog.model_validate(
            {
                "publishers": [
                    {"domain": domain, "name": domain.split(".")[0].title(), "kind": kind}
                    for domain, kind in KINDS.items()
                ],
                "topics": [
                    {
                        "slug": "f1",
                        "name": "F1",
                        "description": "d",
                        "sources": [{"type": "rss", "url": f"https://{d}/feed"} for d in KINDS],
                    }
                ],
            }
        ),
    )
    async with engine.connect() as connection:
        sources = dict((await connection.execute(select(Source.locator, Source.id))).all())
        publishers = dict((await connection.execute(select(Publisher.domain, Publisher.id))).all())
        topic_id: int = (await connection.execute(select(Topic.id))).scalar_one()
    for hours, (domain, title, lead, policy) in enumerate(REPORTS, start=1):
        url = f"https://{domain}/{url_hash(title)[:8]}"
        text = heading_chunk(title, lead)
        await save_document(
            engine,
            NewDocument(
                url=url,
                canonical_url_hash=url_hash(url),
                source_id=sources[f"https://{domain}/feed"],
                publisher_id=publishers[domain],
                title=title,
                lead=lead,
                published_at=NOW - timedelta(hours=hours),
                text_policy=policy,
                policy_reason="test",
                content=None,
                content_purge_after=None,
            ),
            [(text, embeddings.embed_query(text))],
        )
    return topic_id


async def verstappen_note(engine: AsyncEngine, topic_id: int) -> tuple[int, int]:
    """A picked story of the three Verstappen reports, and its note: their ids."""
    async with engine.connect() as connection:
        ids = list(
            (
                await connection.execute(
                    select(Document.id).where(Document.title.startswith("Verstappen"))
                )
            ).scalars()
        )
    edition_id, _ = await db.start_edition(engine, topic_id, NOW.date())
    (story_id,) = await db.save_stories(
        engine, edition_id, [db.NewStory("Verstappen wins", ids, 3, 3.0, [], picked=True)]
    )
    note_id = await db.create_note(engine, story_id, topic_id, NOW.date(), "slug", "note:1")
    return story_id, note_id


async def note_row(engine: AsyncEngine, note_id: int) -> Any:
    async with engine.connect() as connection:
        return (await connection.execute(select(Note).where(Note.id == note_id))).one()


async def test_scout_picks_the_best_stories_a_model_may_read(
    engine: AsyncEngine,
    database_url: str,
    embeddings: Embeddings,
    web: Callable[..., Any],
) -> None:
    topic_id = await seed(engine, embeddings)
    edition_id, _ = await db.start_edition(engine, topic_id, NOW.date())
    deps = ScoutDeps(engine, web({}).http, embeddings, NOW, collect=False)
    async with checkpointer(database_url) as saver:
        state = {"topic_id": topic_id, "slug": "f1", "edition_id": edition_id, "cap": 2}
        result = await build_scout(deps, saver).ainvoke(state, {"configurable": {"thread_id": "s"}})

    async with engine.connect() as connection:
        stories = (await connection.execute(select(Story).order_by(Story.score.desc()))).all()
    assert [(s.title, s.picked) for s in stories] == [
        ("Verstappen wins the United States Grand Prix", True),
        ("Team principal leaves after ten years in charge", False),
        ("Pirelli brings its softest tyres to Mexico City", True),
    ]
    verstappen, link_only, _ = stories
    assert (verstappen.document_count, verstappen.independent_publishers) == (3, 3)
    assert "only link-only reports" in link_only.reasons
    assert result["stories"] == 3
    assert len(result["picked"]) == 2


async def scout_with(
    engine: AsyncEngine,
    database_url: str,
    embeddings: Embeddings,
    web: Callable[..., Any],
    router: ScriptedRouter,
    cap: int,
) -> list[Any]:
    """Scout over the seeded reports with a router that judges relevance; the saved stories,
    best first."""
    topic_id = await seed(engine, embeddings)
    edition_id, _ = await db.start_edition(engine, topic_id, NOW.date())
    deps = ScoutDeps(engine, web({}).http, embeddings, NOW, collect=False, router=router)
    async with checkpointer(database_url) as saver:
        state = {"topic_id": topic_id, "slug": "f1", "edition_id": edition_id, "cap": cap}
        await build_scout(deps, saver).ainvoke(state, {"configurable": {"thread_id": "s"}})
    async with engine.connect() as connection:
        return list((await connection.execute(select(Story).order_by(Story.score.desc()))).all())


async def test_scout_skips_a_story_the_model_finds_off_topic_and_picks_the_next(
    engine: AsyncEngine, database_url: str, embeddings: Embeddings, web: Callable[..., Any]
) -> None:
    """Found 2026-10-17: an "on this day" piece and a petrol pickup's photo gallery were drafted."""
    off = Relevance(on_topic=False, reason="an anniversary piece")
    router = ScriptedRouter({"scout": [off, Relevance(on_topic=True)]})

    verstappen, link_only, pirelli = await scout_with(
        engine, database_url, embeddings, web, router, cap=1
    )

    assert (verstappen.picked, pirelli.picked, link_only.picked) == (False, True, False)
    assert "not about the topic: an anniversary piece" in verstappen.reasons
    # Only readable stories are asked about: the link-only one never reaches a model.
    assert router.calls["scout"] == 2
    assert "Topic: F1" in router.prompts["scout"][0]
    assert "Verstappen wins the United States Grand Prix" in router.prompts["scout"][0]


async def test_scout_picks_unchecked_when_no_model_answers(
    engine: AsyncEngine, database_url: str, embeddings: Embeddings, web: Callable[..., Any]
) -> None:
    router = ScriptedRouter({"scout": [ModelsExhaustedError("scout", [])]})

    verstappen, _, pirelli = await scout_with(engine, database_url, embeddings, web, router, cap=1)

    assert (verstappen.picked, pirelli.picked) == (True, False)
    assert "relevance not checked: no model answered" in verstappen.reasons


async def test_scout_stops_asking_after_the_share_and_the_spare_checks(
    engine: AsyncEngine,
    database_url: str,
    embeddings: Embeddings,
    web: Callable[..., Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(scout_graph, "SPARE_CHECKS", 0)
    router = ScriptedRouter({"scout": [Relevance(on_topic=False, reason="another subject")]})

    stories = await scout_with(engine, database_url, embeddings, web, router, cap=1)

    assert [s.picked for s in stories] == [False, False, False]
    assert router.calls["scout"] == 1


async def test_a_planted_number_is_rewritten_and_the_note_waits_for_approval(
    engine: AsyncEngine, database_url: str, embeddings: Embeddings
) -> None:
    topic_id = await seed(engine, embeddings)
    story_id, note_id = await verstappen_note(engine, topic_id)
    router = ScriptedRouter(
        {
            "researcher": [BRIEF],
            "writer": [PLANTED, CORRECT],
            "extractor": [CLAIMS],
            "verifier": [verdicts([1, 2], [1, 2], [2, 3])],
        }
    )
    config = {"configurable": {"thread_id": "note:1"}}
    async with checkpointer(database_url) as saver:
        graph = build_story_graph(StoryDeps(engine, router, embeddings), saver)

        paused = await graph.ainvoke({"story_id": story_id, "note_id": note_id}, config)

        assert "__interrupt__" in paused
        assert "The number 5.1 is not in the cited evidence" in router.prompts["writer"][1]
        assert (await note_row(engine, note_id)).status == "awaiting_approval"
        _, citations, claims = await db.version_detail(engine, note_id, 2)
        assert [(c.marker, c.publisher) for c in citations] == [
            (1, "Fia"),
            (2, "Wire"),
            (3, "Blog"),
        ]
        assert [(c.verdict, c.independent_origins) for c in claims] == [
            ("supported", 2),
            ("supported", 2),
            ("supported", 2),
        ]
        # Planted and caught by code, so no model checked the first draft.
        assert router.calls == {"researcher": 1, "writer": 2, "extractor": 1, "verifier": 1}

        await graph.ainvoke(
            Command(resume={"decision": "approve", "comment": "ok", "by": "dan review"}), config
        )

    note = await note_row(engine, note_id)
    assert (note.status, note.published_version) == ("published", 2)
    # Indexed for Ask, without its markers.
    assert note.search_text.startswith("Verstappen wins in Austin\nMax Verstappen won")
    assert "[1]" not in note.search_text
    assert note.embedding is not None
    async with engine.connect() as connection:
        approval = (await connection.execute(select(Approval))).one()
    assert (approval.decision, approval.version, approval.decided_by) == (
        "approve",
        2,
        "dan review",
    )


async def test_where_independent_publishers_disagree_the_published_note_says_so(
    engine: AsyncEngine, database_url: str, embeddings: Embeddings
) -> None:
    topic_id = await seed(engine, embeddings)
    story_id, note_id = await verstappen_note(engine, topic_id)
    margin = Disagreement(
        point="The winning margin",
        positions=[
            Position(says="4.2 seconds", evidence=[1]),
            Position(says="5.1 seconds", evidence=[3]),
        ],
    )
    # One publisher on both sides: not a disagreement between publishers.
    itself = Disagreement(
        point="The start",
        positions=[Position(says="pole", evidence=[2]), Position(says="second", evidence=[2])],
    )
    brief = Brief(key_facts=[], disagreements=[margin, itself], angle="Verstappen won.")
    router = ScriptedRouter(
        {
            "researcher": [brief],
            "writer": [CORRECT],
            "extractor": [CLAIMS],
            "verifier": [verdicts([1, 2], [1, 2], [2, 3])],
        }
    )
    config = {"configurable": {"thread_id": "note:1"}}
    async with checkpointer(database_url) as saver:
        graph = build_story_graph(StoryDeps(engine, router, embeddings), saver)
        await graph.ainvoke({"story_id": story_id, "note_id": note_id}, config)
        await graph.ainvoke(
            Command(resume={"decision": "approve", "comment": "", "by": "dan review"}), config
        )
    app = create_app(Settings(_env_file=None))
    app.state.engine = engine  # ASGITransport does not run the lifespan
    transport = httpx2.ASGITransport(app=app)
    async with httpx2.AsyncClient(transport=transport, base_url="http://test") as client:
        note = (await client.get("/api/v1/notes/slug")).json()

    (disagreement,) = note["disagreements"]
    assert disagreement["point"] == "The winning margin"
    assert [
        (p["says"], [(s["marker"], s["publisher"]) for s in p["sources"]])
        for p in disagreement["positions"]
    ] == [("4.2 seconds", [(1, "Fia")]), ("5.1 seconds", [(3, "Blog")])]
    assert "The winning margin" in router.prompts["writer"][0]


async def test_a_weak_claim_reaches_review_after_two_rewrites_and_can_be_rejected(
    engine: AsyncEngine, database_url: str, embeddings: Embeddings
) -> None:
    topic_id = await seed(engine, embeddings)
    story_id, note_id = await verstappen_note(engine, topic_id)
    # The lead in the championship, backed by the specialist blog alone (trust 0.6).
    router = ScriptedRouter(
        {
            "researcher": [BRIEF],
            "writer": [CORRECT],
            "extractor": [CLAIMS],
            "verifier": [verdicts([1, 2], [1, 2], [3])],
        }
    )
    config = {"configurable": {"thread_id": "note:1"}}
    async with checkpointer(database_url) as saver:
        graph = build_story_graph(StoryDeps(engine, router, embeddings), saver)

        await graph.ainvoke({"story_id": story_id, "note_id": note_id}, config)

        assert router.calls["writer"] == 3
        assert "is weak: Only 1 independent origin supports it" in router.prompts["writer"][2]
        _, _, claims = await db.version_detail(engine, note_id, 3)
        assert [c.verdict for c in claims] == ["supported", "supported", "weak"]
        assert (await note_row(engine, note_id)).status == "awaiting_approval"

        await graph.ainvoke(
            Command(resume={"decision": "reject", "comment": "weak", "by": "dan review"}), config
        )

    note = await note_row(engine, note_id)
    assert (note.status, note.published_version) == ("rejected", None)


async def test_an_edition_resumes_where_the_models_ran_out_and_runs_once_a_day(
    engine: AsyncEngine,
    database_url: str,
    embeddings: Embeddings,
    web: Callable[..., Any],
) -> None:
    topic_id = await seed(engine, embeddings)
    scout = ScoutDeps(engine, web({}).http, embeddings, NOW, collect=False)
    out_of_models = ScriptedRouter(
        {**ANY_STORY, "verifier": [ModelsExhaustedError("verifier", ["quota"])]}
    )
    working = ScriptedRouter(ANY_STORY)
    day = NOW.date()
    async with checkpointer(database_url) as saver:
        failed = await run_edition(
            scout,
            StoryDeps(engine, out_of_models, embeddings),
            saver,
            topic_id=topic_id,
            slug="f1",
            day=day,
        )
        assert (failed.status, failed.stories, failed.waiting) == ("failed", 3, [])
        assert len(failed.errors) == 2

        resumed = await run_edition(
            scout,
            StoryDeps(engine, working, embeddings),
            saver,
            topic_id=topic_id,
            slug="f1",
            day=day,
        )
        assert (resumed.status, len(resumed.waiting)) == ("done", 2)
        # Each story graph resumed at the verifier; nothing before it ran again.
        assert working.calls == {"verifier": 2}

        again = await run_edition(
            scout,
            StoryDeps(engine, working, embeddings),
            saver,
            topic_id=topic_id,
            slug="f1",
            day=day,
        )
        assert again.status == "skipped"

    notes = await db.notes(engine, status="awaiting_approval")
    assert len(notes) == 2
    assert len({n.slug for n in notes}) == 2


@pytest.mark.usefixtures("settings_from_env")
async def test_the_owner_reads_and_approves_a_note_with_dan_review(
    engine: AsyncEngine,
    database_url: str,
    embeddings: Embeddings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    topic_id = await seed(engine, embeddings)
    story_id, note_id = await verstappen_note(engine, topic_id)
    router = ScriptedRouter(
        {
            "researcher": [BRIEF],
            "writer": [CORRECT],
            "extractor": [CLAIMS],
            "verifier": [verdicts([1, 2], [1, 2], [3])],
        }
    )
    async with checkpointer(database_url) as saver:
        graph = build_story_graph(StoryDeps(engine, router, embeddings), saver)
        await graph.ainvoke(
            {"story_id": story_id, "note_id": note_id}, {"configurable": {"thread_id": "note:1"}}
        )
    monkeypatch.setenv("DATABASE_URL", database_url)
    # Approving indexes the note; the stand-in keeps the real model (and the network) out.
    monkeypatch.setattr("dailyainotes.cli.LocalEmbeddings", lambda cache_dir: embeddings)

    def dan(*args: str) -> str:
        result = CliRunner().invoke(app, list(args))
        assert result.exit_code == 0, result.output
        return result.output

    # The command line runs its own event loop, so it gets a thread of its own.
    listed = await anyio.to_thread.run_sync(dan, "review", "list")
    shown = await anyio.to_thread.run_sync(dan, "review", "show", "note-1")
    await anyio.to_thread.run_sync(dan, "review", "approve", "note-1")

    assert "note-1" in listed
    assert "2/3 claims supported" in listed
    assert "Why it matters: The win extends his lead in the championship [2][3]." in shown
    assert "[2] Wire" in shown
    assert "weak" in shown
    note = await note_row(engine, note_id)
    assert (note.status, note.published_version) == ("published", 3)


async def test_the_editor_approves_a_note_at_admin_and_the_site_shows_it(
    engine: AsyncEngine, database_url: str, embeddings: Embeddings, access: Any
) -> None:
    topic_id = await seed(engine, embeddings)
    story_id, note_id = await verstappen_note(engine, topic_id)
    router = ScriptedRouter(
        {
            "researcher": [BRIEF],
            "writer": [CORRECT],
            "extractor": [CLAIMS],
            "verifier": [verdicts([1, 2], [1, 2], [2, 3])],
        }
    )
    deps = StoryDeps(engine, router, embeddings)
    async with checkpointer(database_url) as saver:
        await build_story_graph(deps, saver).ainvoke(
            {"story_id": story_id, "note_id": note_id}, {"configurable": {"thread_id": "note:1"}}
        )
    site = create_app(Settings(_env_file=None, database_url=database_url))
    site.state.engine = engine  # ASGITransport does not run the lifespan
    site.state.access = access.verifier  # the team's keys, without the network
    site.dependency_overrides[story_deps] = lambda: deps
    owner = {"Cf-Access-Jwt-Assertion": access.token("Editor@Example.com")}
    stranger = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    forged = {"Cf-Access-Jwt-Assertion": access.token(key=stranger)}

    transport = httpx2.ASGITransport(app=site)
    async with httpx2.AsyncClient(transport=transport, base_url="http://test") as c:
        anonymous = await c.get("/api/v1/admin/notes")
        refused = await c.get("/api/v1/admin/notes", headers=forged)
        me = (await c.get("/api/v1/admin/me", headers=owner)).json()
        (waiting,) = (await c.get("/api/v1/admin/notes", headers=owner)).json()
        decided = await c.post(
            f"/api/v1/admin/notes/{note_id}/decision", json={"decision": "approve"}, headers=owner
        )
        again = await c.post(
            f"/api/v1/admin/notes/{note_id}/decision", json={"decision": "approve"}, headers=owner
        )
        published = (await c.get("/api/v1/notes?date=2026-10-13")).json()

    assert (anonymous.status_code, refused.status_code) == (401, 401)
    assert me == {"email": "editor@example.com"}
    assert waiting["title"] == "Verstappen wins in Austin"
    assert [c["verdict"] for c in waiting["claims"]] == ["supported"] * 3
    assert decided.json() == {"status": "published"}
    assert again.status_code == 409
    (card,) = published["notes"]
    assert (card["sources"], card["supported"], card["claims"]) == (3, 3, 3)
    assert sorted(card["publishers"]) == ["Blog", "Fia", "Wire"]
    async with engine.connect() as connection:
        approval = (await connection.execute(select(Approval))).one()
    assert approval.decided_by == "editor@example.com"


async def test_a_note_shows_how_it_was_made_and_the_reports_it_did_not_cite(
    engine: AsyncEngine, database_url: str, embeddings: Embeddings
) -> None:
    topic_id = await seed(engine, embeddings)
    story_id, note_id = await verstappen_note(engine, topic_id)
    async with engine.begin() as connection:
        # A link-only report merged into the story: no model reads it, so nothing cites it.
        link_only = (
            await connection.execute(select(Document.id).where(Document.title.startswith("Team")))
        ).scalar_one()
        await connection.execute(
            StoryDocument.__table__.insert().values(story_id=story_id, document_id=link_only)
        )
    router = ScriptedRouter(
        {
            "researcher": [BRIEF],
            "writer": [PLANTED, CORRECT],
            "extractor": [CLAIMS],
            "verifier": [verdicts([1, 2], [1, 2], [2, 3])],
        }
    )
    deps = StoryDeps(engine, router, embeddings)
    async with checkpointer(database_url) as saver:
        await build_story_graph(deps, saver).ainvoke(
            {"story_id": story_id, "note_id": note_id}, {"configurable": {"thread_id": "note:1"}}
        )
    await decide_note(deps, database_url, note_id, "approve", "", by="editor@example.com")
    site = create_app(Settings(_env_file=None, database_url=database_url))
    site.state.engine = engine  # ASGITransport does not run the lifespan

    transport = httpx2.ASGITransport(app=site)
    async with httpx2.AsyncClient(transport=transport, base_url="http://test") as c:
        note = (await c.get("/api/v1/notes/slug")).json()

    trail = note["trail"]
    times = [trail[k] for k in ("collected_at", "researched_at", "drafted_at", "approved_at")]
    assert times == sorted(times)
    # The planted number went back to the Writer once.
    assert trail["drafts"] == 2
    assert [(r["title"], r["publisher"]) for r in note["other_reports"]] == [
        ("Team principal leaves after ten years in charge", "Paper")
    ]
    assert "approved_by" not in str(note)


async def test_admin_is_off_without_cloudflare_access(database_url: str) -> None:
    site = create_app(Settings(_env_file=None, database_url=database_url))

    transport = httpx2.ASGITransport(app=site)
    async with httpx2.AsyncClient(transport=transport, base_url="http://test") as c:
        response = await c.get("/api/v1/admin/notes")

    assert response.status_code == 503
    assert "Cloudflare Access is not set up" in response.json()["detail"]


async def test_a_story_from_one_publisher_asks_the_writer_to_attribute_every_fact(
    engine: AsyncEngine, database_url: str, embeddings: Embeddings
) -> None:
    topic_id = await seed(engine, embeddings)
    async with engine.connect() as connection:
        pirelli = (
            await connection.execute(
                select(Document.id).where(Document.title.startswith("Pirelli"))
            )
        ).scalar_one()
    edition_id, _ = await db.start_edition(engine, topic_id, NOW.date())
    (story_id,) = await db.save_stories(
        engine, edition_id, [db.NewStory("Pirelli", [pirelli], 1, 1.0, [], picked=True)]
    )
    note_id = await db.create_note(engine, story_id, topic_id, NOW.date(), "pirelli", "note:1")
    router = ScriptedRouter(ANY_STORY)
    async with checkpointer(database_url) as saver:
        graph = build_story_graph(StoryDeps(engine, router, embeddings), saver)
        await graph.ainvoke(
            {"story_id": story_id, "note_id": note_id}, {"configurable": {"thread_id": "note:1"}}
        )

    assert "All the evidence comes from one publisher, Blog." in router.prompts["writer"][0]
