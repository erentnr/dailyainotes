"""Agent runs and the model usage ledger."""

from datetime import UTC, datetime

from sqlalchemy import func, insert, select, update

from dailyainotes.db.engine import AsyncEngine
from dailyainotes.db.tables import AgentRun, LlmCall
from dailyainotes.domain.llm_usage import CallRecord, Usage


async def start_run(
    engine: AsyncEngine, kind: str, *, topic_id: int | None = None, thread_id: str | None = None
) -> int:
    async with engine.begin() as connection:
        run_id: int = (
            await connection.execute(
                insert(AgentRun)
                .values(kind=kind, topic_id=topic_id, thread_id=thread_id)
                .returning(AgentRun.id)
            )
        ).scalar_one()
    return run_id


async def finish_run(engine: AsyncEngine, run_id: int, status: str, error: str = "") -> None:
    async with engine.begin() as connection:
        await connection.execute(
            update(AgentRun)
            .where(AgentRun.id == run_id)
            .values(status=status, error=error, finished_at=func.now())
        )


class DbLedger:
    """The router's ledger: one `llm_calls` row per request."""

    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine

    async def record(self, run_id: int | None, call: CallRecord) -> None:
        async with self.engine.begin() as connection:
            await connection.execute(insert(LlmCall).values(run_id=run_id, **call.__dict__))

    async def usage_today(self, provider: str) -> Usage:
        """Today in UTC, when the free plans' daily limits reset."""
        midnight = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        async with self.engine.connect() as connection:
            requests, tokens = (
                await connection.execute(
                    select(
                        func.count(),
                        func.coalesce(func.sum(LlmCall.input_tokens + LlmCall.output_tokens), 0),
                    ).where(LlmCall.provider == provider, LlmCall.created_at >= midnight)
                )
            ).one()
        return Usage(requests=requests, tokens=tokens)


async def finish_waiting_runs(engine: AsyncEngine, thread_id: str, status: str) -> None:
    """Close the run that paused this thread, once a decision resumes it."""
    async with engine.begin() as connection:
        await connection.execute(
            update(AgentRun)
            .where(AgentRun.thread_id == thread_id, AgentRun.status == "waiting")
            .values(status=status, finished_at=func.now())
        )
