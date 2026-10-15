"""What the site reads: topics, a day's notes, one note with its sources, a topic's timeline,
and the numbers for How it works. No model is called here."""

from datetime import UTC, date, datetime
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel

from dailyainotes.db import notes as db
from dailyainotes.db.asks import latest_eval_run
from dailyainotes.domain.editorial import without_markers
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


class NoteDetail(NoteCard):
    body: str
    why_it_matters: str
    independent_publishers: int
    citations: list[Citation]


class Timeline(BaseModel):
    topic: Topic
    notes: list[NoteCard]


class DayStats(BaseModel):
    date: date
    notes: int
    model_calls: int
    tokens: int
    cost_usd: float


class Stats(BaseModel):
    totals: dict[str, int]
    days: list[DayStats]
    models: dict[str, str]
    eval: dict[str, Any] | None
    eval_judged: dict[str, Any] | None


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
    return Day(date=day, notes=[card(n) for n in await db.notes_of_day(engine, day, topic)])


@router.get("/notes/{slug}", responses={404: {"description": "No published note"}})
async def note(request: Request, slug: str) -> NoteDetail:
    found = await db.note_by_slug(request.app.state.engine, slug)
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No published note with that slug.")
    published, citations = found
    return NoteDetail(
        **card(published).model_dump(),
        body=published.body,
        why_it_matters=published.why_it_matters,
        independent_publishers=published.independent_publishers,
        citations=[Citation(**vars(c)) for c in citations],
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
    settings = request.app.state.settings
    days = await db.daily_stats(engine, datetime.now(UTC).date(), STATS_DAYS)
    return Stats(
        totals=await db.totals(engine),
        days=[DayStats(**vars(d)) for d in days],
        models={
            "researcher": settings.llm_researcher,
            "writer": settings.llm_writer,
            "extractor": settings.llm_extractor,
            "verifier": settings.llm_verifier,
            "ask": settings.llm_ask,
        },
        eval=await latest_eval_run(engine, "ask"),
        eval_judged=await latest_eval_run(engine, "ask-judged"),
    )
