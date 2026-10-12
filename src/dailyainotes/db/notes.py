"""What the site reads: published notes with their sources and fact-check counts, topics,
and the numbers behind How it works."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import Select, and_, distinct, func, literal, select

from dailyainotes.db.engine import AsyncEngine
from dailyainotes.db.tables import (
    Chunk,
    Citation,
    Claim,
    ClaimCheck,
    Document,
    LlmCall,
    Note,
    NoteVersion,
    Source,
    Story,
    Topic,
)


@dataclass(frozen=True)
class PublishedNote:
    slug: str
    topic: str
    topic_name: str
    edition_date: date
    published_at: datetime
    title: str
    body: str
    why_it_matters: str
    sources: int
    publishers: list[str]
    claims: int
    supported: int
    weak: int
    unsupported: int
    # What Scout merged into the story.
    reports: int
    independent_publishers: int


@dataclass(frozen=True)
class TopicRow:
    slug: str
    name: str
    description: str
    notes: int


@dataclass(frozen=True)
class CitationOut:
    marker: int
    title: str
    url: str
    publisher: str
    published_at: datetime | None
    quote: str


@dataclass(frozen=True)
class DayStats:
    date: date
    notes: int
    model_calls: int
    tokens: int
    cost_usd: float


def published_notes() -> Select[*tuple[Any, ...]]:
    citations = (
        select(
            Citation.note_version_id,
            func.count().label("sources"),
            func.array_agg(distinct(Citation.publisher)).label("publishers"),
        )
        .group_by(Citation.note_version_id)
        .subquery()
    )
    checks = (
        select(
            Claim.note_version_id,
            func.count().label("claims"),
            func.count().filter(ClaimCheck.verdict == "supported").label("supported"),
            func.count().filter(ClaimCheck.verdict == "weak").label("weak"),
            func.count()
            .filter(ClaimCheck.verdict.in_(["unsupported", "contradicted"]))
            .label("unsupported"),
        )
        .join(ClaimCheck, ClaimCheck.claim_id == Claim.id)
        .group_by(Claim.note_version_id)
        .subquery()
    )
    return (
        select(
            Note.slug,
            Topic.slug,
            Topic.name,
            Note.edition_date,
            Note.published_at,
            NoteVersion.title,
            NoteVersion.body,
            NoteVersion.why_it_matters,
            func.coalesce(citations.c.sources, 0),
            func.coalesce(citations.c.publishers, literal([])),
            func.coalesce(checks.c.claims, 0),
            func.coalesce(checks.c.supported, 0),
            func.coalesce(checks.c.weak, 0),
            func.coalesce(checks.c.unsupported, 0),
            Story.document_count,
            Story.independent_publishers,
        )
        .join(Topic, Topic.id == Note.topic_id)
        .join(
            NoteVersion,
            and_(NoteVersion.note_id == Note.id, NoteVersion.version == Note.published_version),
        )
        .join(Story, Story.id == Note.story_id)
        .outerjoin(citations, citations.c.note_version_id == NoteVersion.id)
        .outerjoin(checks, checks.c.note_version_id == NoteVersion.id)
        .where(Note.status == "published")
        .order_by(Note.edition_date.desc(), Note.published_at.desc(), Note.id.desc())
    )


async def _fetch(engine: AsyncEngine, statement: Select[*tuple[Any, ...]]) -> list[PublishedNote]:
    async with engine.connect() as connection:
        notes = []
        for row in await connection.execute(statement):
            values = list(row)
            values[9] = list(values[9])  # publishers: a Postgres array
            notes.append(PublishedNote(*values))
        return notes


async def latest_day(engine: AsyncEngine, topics: list[str], today: date) -> date | None:
    """The most recent day, up to today, with a published note on one of the topics."""
    statement = (
        select(func.max(Note.edition_date))
        .join(Topic, Topic.id == Note.topic_id)
        .where(Note.status == "published", Note.edition_date <= today)
    )
    if topics:
        statement = statement.where(Topic.slug.in_(topics))
    async with engine.connect() as connection:
        day: date | None = (await connection.execute(statement)).scalar_one()
    return day


async def notes_of_day(engine: AsyncEngine, day: date, topics: list[str]) -> list[PublishedNote]:
    statement = published_notes().where(Note.edition_date == day)
    if topics:
        statement = statement.where(Topic.slug.in_(topics))
    return await _fetch(engine, statement)


async def topic_timeline(
    engine: AsyncEngine, topic: str, *, before: date | None, limit: int
) -> list[PublishedNote]:
    statement = published_notes().where(Topic.slug == topic).limit(limit)
    if before:
        statement = statement.where(Note.edition_date < before)
    return await _fetch(engine, statement)


async def note_by_slug(
    engine: AsyncEngine, slug: str
) -> tuple[PublishedNote, list[CitationOut]] | None:
    found = await _fetch(engine, published_notes().where(Note.slug == slug))
    if not found:
        return None
    statement = (
        select(
            Citation.marker,
            Citation.title,
            Citation.url,
            Citation.publisher,
            Citation.published_at,
            Citation.quote,
        )
        .join(NoteVersion, NoteVersion.id == Citation.note_version_id)
        .join(
            Note,
            and_(Note.id == NoteVersion.note_id, Note.published_version == NoteVersion.version),
        )
        .where(Note.slug == slug)
        .order_by(Citation.marker)
    )
    async with engine.connect() as connection:
        citations = [CitationOut(*row) for row in await connection.execute(statement)]
    return found[0], citations


async def active_topics(engine: AsyncEngine) -> list[TopicRow]:
    published = (
        select(Note.topic_id, func.count().label("notes"))
        .where(Note.status == "published")
        .group_by(Note.topic_id)
        .subquery()
    )
    statement = (
        select(Topic.slug, Topic.name, Topic.description, func.coalesce(published.c.notes, 0))
        .outerjoin(published, published.c.topic_id == Topic.id)
        .where(Topic.status == "active")
        .order_by(Topic.name)
    )
    async with engine.connect() as connection:
        return [TopicRow(*row) for row in await connection.execute(statement)]


async def totals(engine: AsyncEngine) -> dict[str, int]:
    async with engine.connect() as connection:
        row = (
            await connection.execute(
                select(
                    select(func.count()).where(Note.status == "published").scalar_subquery(),
                    select(func.count()).where(Topic.status == "active").scalar_subquery(),
                    select(func.count()).select_from(Source).scalar_subquery(),
                    select(func.count()).select_from(Document).scalar_subquery(),
                    select(func.count()).select_from(Chunk).scalar_subquery(),
                )
            )
        ).one()
    names = ["notes_published", "topics_active", "sources", "documents", "chunks"]
    return dict(zip(names, row, strict=True))


async def daily_stats(engine: AsyncEngine, today: date, days: int) -> list[DayStats]:
    """Notes published and model use per UTC day, oldest first, zeros included."""
    since = today - timedelta(days=days - 1)
    call_day = func.date(func.timezone("UTC", LlmCall.created_at))
    note_day = func.date(func.timezone("UTC", Note.published_at))
    async with engine.connect() as connection:
        calls = {
            row[0]: row[1:]
            for row in await connection.execute(
                select(
                    call_day,
                    func.count(),
                    func.sum(LlmCall.input_tokens + LlmCall.output_tokens),
                    func.sum(LlmCall.cost_usd),
                )
                .where(call_day >= since)
                .group_by(call_day)
            )
        }
        notes: dict[date, int] = dict(
            (
                await connection.execute(
                    select(note_day, func.count())
                    .where(Note.status == "published", note_day >= since)
                    .group_by(note_day)
                )
            ).all()
        )
    stats = []
    for offset in range(days):
        day = since + timedelta(days=offset)
        count, tokens, cost = calls.get(day, (0, 0, 0.0))
        stats.append(DayStats(day, notes.get(day, 0), count, int(tokens), float(cost)))
    return stats
