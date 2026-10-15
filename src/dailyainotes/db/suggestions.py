"""Topic suggestions: readers propose topics, and the editor accepts or declines them."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, insert, select, update

from dailyainotes.db.engine import AsyncEngine
from dailyainotes.db.tables import Topic, TopicSuggestion
from dailyainotes.domain.accounts import topic_slug


class NotOpenError(Exception):
    """The suggestion was already accepted or declined, or does not exist."""


@dataclass(frozen=True)
class ReaderSuggestion:
    id: int
    name: str
    note: str
    status: str
    reason: str
    created_at: datetime
    # Once accepted: the topic made from it, and whether it is active yet.
    topic_slug: str | None
    topic_status: str | None


@dataclass(frozen=True)
class OpenSuggestion:
    id: int
    name: str
    note: str
    created_at: datetime


async def open_count(engine: AsyncEngine, reader_id: int) -> int:
    async with engine.connect() as connection:
        count: int = (
            await connection.execute(
                select(func.count())
                .select_from(TopicSuggestion)
                .where(TopicSuggestion.reader_id == reader_id, TopicSuggestion.status == "open")
            )
        ).scalar_one()
    return count


async def add(engine: AsyncEngine, reader_id: int, name: str, note: str) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            insert(TopicSuggestion).values(reader_id=reader_id, name=name, note=note)
        )


async def for_reader(engine: AsyncEngine, reader_id: int) -> list[ReaderSuggestion]:
    async with engine.connect() as connection:
        rows = await connection.execute(
            select(
                TopicSuggestion.id,
                TopicSuggestion.name,
                TopicSuggestion.note,
                TopicSuggestion.status,
                TopicSuggestion.reason,
                TopicSuggestion.created_at,
                Topic.slug,
                Topic.status,
            )
            .outerjoin(Topic, Topic.id == TopicSuggestion.topic_id)
            .where(TopicSuggestion.reader_id == reader_id)
            .order_by(TopicSuggestion.created_at.desc(), TopicSuggestion.id.desc())
        )
        return [ReaderSuggestion(*row) for row in rows]


async def waiting(engine: AsyncEngine) -> list[OpenSuggestion]:
    async with engine.connect() as connection:
        rows = await connection.execute(
            select(
                TopicSuggestion.id,
                TopicSuggestion.name,
                TopicSuggestion.note,
                TopicSuggestion.created_at,
            )
            .where(TopicSuggestion.status == "open")
            .order_by(TopicSuggestion.created_at, TopicSuggestion.id)
        )
        return [OpenSuggestion(*row) for row in rows]


async def accept(engine: AsyncEngine, suggestion_id: int, by: str) -> str:
    """Make a draft topic from the suggestion; the new topic's slug."""
    async with engine.begin() as connection:
        found = (
            await connection.execute(
                select(TopicSuggestion.name, TopicSuggestion.note)
                .where(TopicSuggestion.id == suggestion_id, TopicSuggestion.status == "open")
                .with_for_update()
            )
        ).one_or_none()
        if found is None:
            raise NotOpenError(f"suggestion-{suggestion_id} is not waiting for a decision")
        name, note = found
        taken = set((await connection.execute(select(Topic.slug))).scalars())
        slug = topic_slug(name, taken)
        topic_id = (
            await connection.execute(
                insert(Topic)
                .values(slug=slug, name=name, description=note or name, status="draft")
                .returning(Topic.id)
            )
        ).scalar_one()
        await connection.execute(
            update(TopicSuggestion)
            .where(TopicSuggestion.id == suggestion_id)
            .values(status="accepted", topic_id=topic_id, decided_at=func.now(), decided_by=by)
        )
    return slug


async def decline(engine: AsyncEngine, suggestion_id: int, reason: str, by: str) -> None:
    async with engine.begin() as connection:
        declined = await connection.execute(
            update(TopicSuggestion)
            .where(TopicSuggestion.id == suggestion_id, TopicSuggestion.status == "open")
            .values(status="declined", reason=reason, decided_at=func.now(), decided_by=by)
        )
        if declined.rowcount == 0:
            raise NotOpenError(f"suggestion-{suggestion_id} is not waiting for a decision")
