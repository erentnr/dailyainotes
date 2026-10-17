"""What the site reads: topics, a day's notes, one note with its sources, a topic's timeline,
and the numbers for How it works. No model is called here."""

from datetime import UTC, date, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel

from dailyainotes.accounts import signed_in
from dailyainotes.api.accounts import COOKIE, Reader, SameOrigin
from dailyainotes.db import notes as db
from dailyainotes.domain.editorial import without_markers
from dailyainotes.domain.matching import preferences
from dailyainotes.domain.topics import TopicCategory

router = APIRouter()
STATS_DAYS = 14


class Topic(BaseModel):
    slug: str
    name: str
    description: str
    # Picks the topic's cover and its group in the picker; null draws the plain cover.
    category: TopicCategory | None
    notes: int


class NoteCard(BaseModel):
    slug: str
    topic: str
    topic_name: str
    edition_date: date
    published_at: datetime
    title: str
    summary: str
    sources: int
    publishers: list[str]
    claims: int
    supported: int
    weak: int
    unsupported: int
    # Reports Scout merged into the story ("9 reports → 1").
    reports: int
    # For a signed-in reader who marked notes "more" or "less like this": how much they may
    # prefer this one; the page orders by it (ADR 0007). Null otherwise.
    preference: float | None = None


class Day(BaseModel):
    # The day shown: the one asked for, or the latest with notes on the topics.
    date: date | None
    notes: list[NoteCard]


class Citation(BaseModel):
    marker: int
    title: str
    url: str
    publisher: str
    published_at: datetime | None
    quote: str


class Trail(BaseModel):
    """When each step happened: Scout's run on the topic, the Researcher, the Writer's first
    draft, and the editor's approval. The fact-check keeps no time of its own."""

    collected_at: datetime
    researched_at: datetime
    drafted_at: datetime | None
    # The Writer's drafts, rewrites after the fact-check included.
    drafts: int
    approved_at: datetime | None


class Report(BaseModel):
    title: str
    url: str
    publisher: str
    published_at: datetime | None


class PositionSource(BaseModel):
    # The evidence number; it matches the note's citation marker when the note cites it.
    marker: int
    publisher: str
    title: str
    url: str


class Position(BaseModel):
    # In our own words, as the research brief put it: never a quote.
    says: str
    sources: list[PositionSource]


class Disagreement(BaseModel):
    point: str
    positions: list[Position]


class NoteDetail(NoteCard):
    body: str
    why_it_matters: str
    independent_publishers: int
    citations: list[Citation]
    trail: Trail
    # Reports merged into the story that no sentence cites: linked, never quoted.
    other_reports: list[Report]
    # Where publishers with no owner in common disagree.
    disagreements: list[Disagreement] = []


class Timeline(BaseModel):
    topic: Topic
    notes: list[NoteCard]


class DayStats(BaseModel):
    date: date
    notes: int


class Stats(BaseModel):
    """What readers see on How it works. Cost, model use, model names and eval scores stay ours:
    they are in llm_calls, eval_runs and the logs."""

    totals: dict[str, int]
    days: list[DayStats]


def card(note: db.PublishedNote) -> NoteCard:
    return NoteCard(
        slug=note.slug,
        topic=note.topic,
        topic_name=note.topic_name,
        edition_date=note.edition_date,
        published_at=note.published_at,
        title=note.title,
        summary=without_markers(note.body),
        sources=note.sources,
        publishers=note.publishers,
        claims=note.claims,
        supported=note.supported,
        weak=note.weak,
        unsupported=note.unsupported,
        reports=note.reports,
    )


@router.get("/topics")
async def topics(request: Request) -> list[Topic]:
    return [Topic(**vars(t)) for t in await db.active_topics(request.app.state.engine)]


@router.get("/notes")
async def notes_of_day(
    request: Request,
    topic: Annotated[list[str], Query(max_length=20)] = [],  # noqa: B006 (FastAPI copies it)
    day: Annotated[date | None, Query(alias="date")] = None,
) -> Day:
    engine = request.app.state.engine
    day = day or await db.latest_day(engine, topic, datetime.now(UTC).date())
    if day is None:
        return Day(date=None, notes=[])
    cards = [card(n) for n in await db.notes_of_day(engine, day, topic)]
    reader_id = await reader_of(request)
    if reader_id is not None and cards:
        liked, disliked = await db.feedback_vectors(engine, reader_id)
        vectors = await db.note_vectors(engine, [c.slug for c in cards])
        scores = preferences(vectors, liked, disliked)
        cards = [c.model_copy(update={"preference": scores.get(c.slug)}) for c in cards]
    return Day(date=day, notes=cards)


async def reader_of(request: Request) -> int | None:
    """The signed-in reader, when the request carries a session cookie; reading needs none."""
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    found = await signed_in(request.app.state.engine, token, datetime.now(UTC))
    return found.reader_id if found else None


class Feedback(BaseModel):
    # 1 for "more like this", -1 for "less like this", 0 for neither.
    value: Literal[-1, 0, 1]


@router.get("/me/notes/{slug}/feedback", responses={401: {}})
async def get_feedback(request: Request, slug: str, found: Reader) -> Feedback:
    value = await db.feedback_on(request.app.state.engine, found.reader_id, slug)
    return Feedback(value=1 if value > 0 else -1 if value < 0 else 0)


@router.put(
    "/me/notes/{slug}/feedback",
    dependencies=[SameOrigin],
    responses={401: {}, 404: {"description": "No published note"}},
)
async def put_feedback(request: Request, slug: str, body: Feedback, found: Reader) -> Feedback:
    """A reader's "more like this" or "less like this" on a note, kept with the account."""
    if not await db.set_feedback(request.app.state.engine, found.reader_id, slug, body.value):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No published note with that slug.")
    return body


@router.get("/notes/{slug}", responses={404: {"description": "No published note"}})
async def note(request: Request, slug: str) -> NoteDetail:
    engine = request.app.state.engine
    found = await db.note_by_slug(engine, slug)
    made = await db.note_trail(engine, slug)
    if found is None or made is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No published note with that slug.")
    published, citations = found
    trail, others = made
    return NoteDetail(
        **card(published).model_dump(),
        body=published.body,
        why_it_matters=published.why_it_matters,
        independent_publishers=published.independent_publishers,
        citations=[Citation(**vars(c)) for c in citations],
        trail=Trail(**vars(trail)),
        other_reports=[Report(**vars(r)) for r in others],
        disagreements=[Disagreement(**d) for d in published.disagreements],
    )


@router.get("/topics/{slug}/notes", responses={404: {"description": "No active topic"}})
async def timeline(
    request: Request,
    slug: str,
    before: date | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> Timeline:
    engine = request.app.state.engine
    topics = {t.slug: t for t in await db.active_topics(engine)}
    if slug not in topics:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No active topic with that slug.")
    notes = await db.topic_timeline(engine, slug, before=before, limit=limit)
    return Timeline(topic=Topic(**vars(topics[slug])), notes=[card(n) for n in notes])


@router.get("/stats")
async def stats(request: Request) -> Stats:
    engine = request.app.state.engine
    days = await db.daily_stats(engine, datetime.now(UTC).date(), STATS_DAYS)
    return Stats(totals=await db.totals(engine), days=[DayStats(**vars(d)) for d in days])
