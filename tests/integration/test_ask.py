from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx2
import pytest
from fastapi import Request
from langchain_core.embeddings import Embeddings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine

from dailyainotes.accounts import delete_account, open_session
from dailyainotes.api.accounts import AccountDeps
from dailyainotes.api.app import create_app
from dailyainotes.api.deps import ask_deps
from dailyainotes.ask import AskDeps, Asker, ask, purge
from dailyainotes.db.asks import count_request
from dailyainotes.db.tables import AskRequest, Note, RateLimit
from dailyainotes.domain.answers import NOT_ENOUGH
from dailyainotes.evals import EVALS, CorpusNote, load_corpus, read_jsonl
from dailyainotes.llm.router import ModelsExhaustedError
from dailyainotes.settings import Settings

pytestmark = [pytest.mark.integration, pytest.mark.anyio]

# Full-text search finds the battery note for this question, whatever the stand-in vectors say.
COVERED = "Brightwater iron-air battery"
UNCOVERED = "How many legs does a spider have?"


class StreamingRouter:
    """Streams its pieces, or raises; records each prompt."""

    def __init__(self, pieces: list[str] | Exception) -> None:
        self.pieces = pieces
        self.prompts: list[str] = []

    async def stream(
        self, role: str, *, system: str, user: str, run_id: int | None = None
    ) -> AsyncIterator[str]:
        self.prompts.append(user)
        if isinstance(self.pieces, Exception):
            raise self.pieces
        for piece in self.pieces:
            yield piece


async def corpus(engine: AsyncEngine, embeddings: Embeddings) -> None:
    """The first five eval notes (climate tech), published and indexed."""
    notes = read_jsonl(EVALS / "corpus.jsonl", CorpusNote)[:5]
    await load_corpus(engine, AskDeps(engine, embeddings, StreamingRouter([])), notes)


async def events(deps: AskDeps, question: str) -> list[tuple[str, Any]]:
    """The events for a question a signed-in reader asks from the site."""
    session = await open_session(deps.engine, "reader@example.com", datetime.now(UTC))
    asker = Asker(session.reader_id, "visitor")
    return [event async for event in ask(deps, question, [], asker=asker)]


async def logged(engine: AsyncEngine) -> list[Any]:
    async with engine.connect() as connection:
        return list(await connection.execute(select(AskRequest)))


async def test_a_covered_question_streams_an_answer_whose_citations_are_checked(
    engine: AsyncEngine, embeddings: Embeddings
) -> None:
    await corpus(engine, embeddings)
    router = StreamingRouter(["The pilot can discharge for 100 hours [1]", ". It is large [4]."])

    result = await events(AskDeps(engine, embeddings, router), COVERED)

    kinds = [kind for kind, _ in result]
    assert kinds[0] == "sources"
    assert kinds[-1] == "done"
    sources = result[0][1]
    assert sources[0]["slug"].endswith(
        "brightwater-energy-starts-a-100-hour-iron-air-battery-pilot"
    )
    text = "".join(data for kind, data in result if kind == "text")
    assert text == "The pilot can discharge for 100 hours [1]. It is large."
    assert result[-1][1] == {"insufficient": False, "cited": [1]}
    assert "<question>\nBrightwater iron-air battery\n</question>" in router.prompts[0]
    async with engine.connect() as connection:
        battery = (
            await connection.execute(select(Note.id).where(Note.slug == sources[0]["slug"]))
        ).scalar_one()
    (row,) = await logged(engine)
    assert (row.ip_hash, row.cited_note_ids, row.insufficient) == ("visitor", [battery], False)


async def test_an_uncovered_question_gets_not_enough_without_a_model_call(
    engine: AsyncEngine, embeddings: Embeddings
) -> None:
    await corpus(engine, embeddings)
    router = StreamingRouter(ModelsExhaustedError("ask", ["should not be called"]))

    result = await events(AskDeps(engine, embeddings, router), UNCOVERED)

    assert result == [
        ("sources", []),
        ("text", NOT_ENOUGH),
        ("done", {"insufficient": True, "cited": []}),
    ]
    assert router.prompts == []
    (row,) = await logged(engine)
    assert row.insufficient


async def test_a_question_reads_only_the_notes_of_the_days_asked_about(
    engine: AsyncEngine, embeddings: Embeddings
) -> None:
    await corpus(engine, embeddings)
    router = StreamingRouter(["Yes [1]."])
    deps = AskDeps(engine, embeddings, router)

    async def found(since: date | None, until: date | None) -> list[str]:
        result = [event async for event in ask(deps, COVERED, [], since=since, until=until)]
        return [s["edition_date"].isoformat() for s in result[0][1]]

    # The Brightwater note is from 2026-09-02.
    assert await found(date(2026, 9, 2), date(2026, 9, 2)) == ["2026-09-02"]
    assert await found(date(2026, 9, 3), None) == []
    assert await found(None, date(2026, 9, 1)) == []
    assert len(router.prompts) == 1


async def test_a_model_that_finds_the_notes_lacking_is_shown_as_not_enough(
    engine: AsyncEngine, embeddings: Embeddings
) -> None:
    await corpus(engine, embeddings)

    result = await events(AskDeps(engine, embeddings, StreamingRouter(["NOT_", "ENOUGH"])), COVERED)

    assert [event for event in result if event[0] != "sources"] == [
        ("text", NOT_ENOUGH),
        ("done", {"insufficient": True, "cited": []}),
    ]


async def test_no_model_answering_ends_the_stream_with_an_error(
    engine: AsyncEngine, embeddings: Embeddings
) -> None:
    await corpus(engine, embeddings)
    router = StreamingRouter(ModelsExhaustedError("ask", ["quota"]))

    result = await events(AskDeps(engine, embeddings, router), COVERED)

    assert [kind for kind, _ in result] == ["sources", "error"]
    (row,) = await logged(engine)
    assert row.insufficient


def asking_site(engine: AsyncEngine, embeddings: Embeddings) -> httpx2.AsyncClient:
    """The API with a model that finds the notes lacking; every visitor comes from one IP."""
    app = create_app(Settings(_env_file=None))
    # ASGITransport does not run the lifespan, so the test's engine stands in for its own.
    app.state.engine = engine
    app.state.accounts = AccountDeps(engine, None, None, "http://test")

    def deps(request: Request) -> AskDeps:
        return AskDeps(engine, embeddings, StreamingRouter([]))

    app.dependency_overrides[ask_deps] = deps
    transport = httpx2.ASGITransport(app=app)
    return httpx2.AsyncClient(transport=transport, base_url="http://test")


async def sign_in(engine: AsyncEngine, site: httpx2.AsyncClient, email: str) -> int:
    """Open a session for the reader and send its cookie from now on; the reader's id."""
    session = await open_session(engine, email, datetime.now(UTC))
    site.cookies.set("dan_session", session.token)
    return session.reader_id


async def test_asking_needs_a_signed_in_reader(engine: AsyncEngine, embeddings: Embeddings) -> None:
    async with asking_site(engine, embeddings) as site:
        anonymous = await site.post("/api/v1/ask", json={"question": UNCOVERED})

    assert anonymous.status_code == 401
    assert await logged(engine) == []


async def test_the_api_streams_events_and_allows_ten_questions_per_reader_a_day(
    engine: AsyncEngine, embeddings: Embeddings
) -> None:
    async with asking_site(engine, embeddings) as site:
        reader_id = await sign_in(engine, site, "reader@example.com")
        answers = [await site.post("/api/v1/ask", json={"question": UNCOVERED}) for _ in range(10)]
        refused = await site.post("/api/v1/ask", json={"question": UNCOVERED})
        too_short = await site.post("/api/v1/ask", json={"question": "?"})
        backwards = await site.post(
            "/api/v1/ask",
            json={"question": UNCOVERED, "since": "2026-10-02", "until": "2026-10-01"},
        )

    assert {a.status_code for a in answers} == {200}
    assert answers[0].headers["content-type"].startswith("text/event-stream")
    assert answers[0].text == (
        "event: sources\ndata: []\n\n"
        f'event: text\ndata: "{NOT_ENOUGH}"\n\n'
        'event: done\ndata: {"insufficient": true, "cited": []}\n\n'
    )
    assert refused.status_code == 429
    assert "10 questions" in refused.json()["detail"]
    assert too_short.status_code == 422
    assert backwards.status_code == 422
    rows = await logged(engine)
    assert len(rows) == 10
    assert {row.reader_id for row in rows} == {reader_id}


async def test_one_connection_shares_thirty_questions_a_day_between_its_readers(
    engine: AsyncEngine, embeddings: Embeddings
) -> None:
    statuses = []
    async with asking_site(engine, embeddings) as site:
        for n in range(4):
            await sign_in(engine, site, f"reader{n}@example.com")
            for _ in range(10 if n < 3 else 1):
                response = await site.post("/api/v1/ask", json={"question": UNCOVERED})
                statuses.append((n, response.status_code, response.text))

    assert {code for n, code, _ in statuses if n < 3} == {200}
    ((_, code, text),) = [s for s in statuses if s[0] == 3]
    assert code == 429
    assert "30 questions" in text


async def test_the_site_answers_two_hundred_questions_a_day_in_all(
    engine: AsyncEngine, embeddings: Embeddings
) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            RateLimit.__table__.insert().values(key="all", day=datetime.now(UTC).date(), count=199)
        )
    async with asking_site(engine, embeddings) as site:
        await sign_in(engine, site, "reader@example.com")
        last = await site.post("/api/v1/ask", json={"question": UNCOVERED})
        refused = await site.post("/api/v1/ask", json={"question": UNCOVERED})

    assert last.status_code == 200
    assert refused.status_code == 429
    assert "all the questions it can today" in refused.json()["detail"]


async def test_deleting_an_account_deletes_its_questions(
    engine: AsyncEngine, embeddings: Embeddings
) -> None:
    async with asking_site(engine, embeddings) as site:
        reader_id = await sign_in(engine, site, "reader@example.com")
        await site.post("/api/v1/ask", json={"question": UNCOVERED})
        await sign_in(engine, site, "other@example.com")
        await site.post("/api/v1/ask", json={"question": UNCOVERED})

    await delete_account(engine, reader_id)

    assert [row.reader_id for row in await logged(engine)] == [reader_id + 1]


async def test_old_questions_and_counts_are_purged(
    engine: AsyncEngine, embeddings: Embeddings
) -> None:
    await events(AskDeps(engine, embeddings, StreamingRouter([])), UNCOVERED)
    today = datetime.now(UTC)
    await count_request(engine, "all", today.date() - timedelta(days=2))
    await count_request(engine, "all", today.date())

    await purge(engine, today + timedelta(days=31))

    assert await logged(engine) == []
    async with engine.connect() as connection:
        days = list((await connection.execute(select(RateLimit.day))).scalars())
    assert days == []

    await count_request(engine, "all", today.date())
    await purge(engine, today)
    async with engine.connect() as connection:
        days = list((await connection.execute(select(RateLimit.day))).scalars())
    assert days == [today.date()]
