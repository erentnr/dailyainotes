"""The Ask log, rate-limit counters and eval runs."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy import delete, insert, select
from sqlalchemy.dialects.postgresql import insert as upsert

from dailyainotes.db.engine import AsyncEngine
from dailyainotes.db.tables import AskRequest, EvalRun, RateLimit


async def count_request(engine: AsyncEngine, key: str, day: date) -> int:
    """Add one request for the key and day; the day's count so far, this one included."""
    statement = (
        upsert(RateLimit)
        .values(key=key, day=day, count=1)
        .on_conflict_do_update(index_elements=["key", "day"], set_={"count": RateLimit.count + 1})
        .returning(RateLimit.count)
    )
    async with engine.begin() as connection:
        count: int = (await connection.execute(statement)).scalar_one()
    return count


async def log_ask(
    engine: AsyncEngine,
    reader_id: int,
    ip_hash: str,
    question: str,
    cited_note_ids: list[int],
    insufficient: bool,
) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            insert(AskRequest).values(
                reader_id=reader_id,
                ip_hash=ip_hash,
                question=question,
                cited_note_ids=cited_note_ids,
                insufficient=insufficient,
            )
        )


@dataclass(frozen=True)
class LoggedQuestion:
    question: str
    asked_at: datetime
    insufficient: bool
    cited_note_ids: list[int]


async def questions_of(
    engine: AsyncEngine, reader_id: int, since: datetime
) -> list[LoggedQuestion]:
    """The reader's questions to Ask since then, newest first."""
    async with engine.connect() as connection:
        rows = await connection.execute(
            select(
                AskRequest.question,
                AskRequest.created_at,
                AskRequest.insufficient,
                AskRequest.cited_note_ids,
            )
            .where(AskRequest.reader_id == reader_id, AskRequest.created_at >= since)
            .order_by(AskRequest.created_at.desc(), AskRequest.id.desc())
        )
        return [LoggedQuestion(*row) for row in rows]


async def purge_asks(engine: AsyncEngine, *, log_before: datetime, counts_before: date) -> None:
    async with engine.begin() as connection:
        await connection.execute(delete(AskRequest).where(AskRequest.created_at < log_before))
        await connection.execute(delete(RateLimit).where(RateLimit.day < counts_before))


async def record_eval_run(
    engine: AsyncEngine, suite: str, git_sha: str, metrics: dict[str, Any]
) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            insert(EvalRun).values(suite=suite, git_sha=git_sha, metrics=metrics)
        )
