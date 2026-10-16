"""The Ask log, rate-limit counters and eval runs."""

from datetime import date, datetime
from typing import Any

from sqlalchemy import delete, insert
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
