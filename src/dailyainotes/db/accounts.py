"""Readers, their sign-in codes, sessions and topics (ADR 0003)."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as upsert

from dailyainotes.db.engine import AsyncEngine
from dailyainotes.db.tables import Reader, ReaderSession, ReaderTopic, SignInCode, Topic


@dataclass(frozen=True)
class LiveCode:
    id: int
    email: str
    code_digest: str
    attempts: int


@dataclass(frozen=True)
class SessionReader:
    id: int
    email: str
    expires_at: datetime
    last_used_at: datetime


@dataclass(frozen=True)
class FollowedTopic:
    slug: str
    slot: int


async def codes_sent_since(engine: AsyncEngine, email: str, since: datetime) -> int:
    async with engine.connect() as connection:
        count: int = (
            await connection.execute(
                select(func.count())
                .select_from(SignInCode)
                .where(SignInCode.email == email, SignInCode.created_at >= since)
            )
        ).scalar_one()
    return count


async def save_code(
    engine: AsyncEngine, email: str, code_digest: str, link_digest: str, expires_at: datetime
) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            insert(SignInCode).values(
                email=email,
                code_digest=code_digest,
                link_digest=link_digest,
                expires_at=expires_at,
            )
        )


async def spend_try(
    engine: AsyncEngine, email: str, now: datetime, max_attempts: int
) -> LiveCode | None:
    """Count one try at the newest code sent to the address that is unused, unexpired and not
    voided by too many wrong tries, and return it with the tries counted so far; None when no
    code is left. Counting before the code is compared, in one conditional statement, keeps
    the limit when tries arrive together: Postgres checks `attempts` again on the locked row."""
    newest = (
        select(SignInCode.id)
        .where(
            SignInCode.email == email,
            SignInCode.used_at.is_(None),
            SignInCode.expires_at > now,
            SignInCode.attempts < max_attempts,
        )
        .order_by(SignInCode.created_at.desc(), SignInCode.id.desc())
        .limit(1)
        .scalar_subquery()
    )
    async with engine.begin() as connection:
        row = (
            await connection.execute(
                update(SignInCode)
                .where(
                    SignInCode.id == newest,
                    SignInCode.used_at.is_(None),
                    SignInCode.attempts < max_attempts,
                )
                .values(attempts=SignInCode.attempts + 1)
                .returning(
                    SignInCode.id, SignInCode.email, SignInCode.code_digest, SignInCode.attempts
                )
            )
        ).one_or_none()
    return LiveCode(*row) if row else None


async def live_code_for_link(
    engine: AsyncEngine, link_digest: str, now: datetime, max_attempts: int
) -> str | None:
    """The email a live link was sent to; too many wrong codes void the link as well."""
    async with engine.connect() as connection:
        email: str | None = (
            await connection.execute(
                select(SignInCode.email).where(
                    SignInCode.link_digest == link_digest,
                    SignInCode.used_at.is_(None),
                    SignInCode.expires_at > now,
                    SignInCode.attempts < max_attempts,
                )
            )
        ).scalar_one_or_none()
    return email


async def sign_in(
    engine: AsyncEngine, email: str, session_digest: str, expires_at: datetime, now: datetime
) -> int:
    """Use up every live code for the address, make the reader if new, and open a session, in
    one transaction. The reader's id."""
    async with engine.begin() as connection:
        await connection.execute(
            update(SignInCode)
            .where(SignInCode.email == email, SignInCode.used_at.is_(None))
            .values(used_at=now)
        )
        reader_id: int = (
            await connection.execute(
                upsert(Reader)
                .values(email=email, last_seen_at=now)
                .on_conflict_do_update(index_elements=["email"], set_={"last_seen_at": now})
                .returning(Reader.id)
            )
        ).scalar_one()
        await connection.execute(
            insert(ReaderSession).values(
                token_digest=session_digest,
                reader_id=reader_id,
                expires_at=expires_at,
                last_used_at=now,
            )
        )
    return reader_id


async def session_reader(
    engine: AsyncEngine, session_digest: str, now: datetime
) -> SessionReader | None:
    async with engine.connect() as connection:
        row = (
            await connection.execute(
                select(
                    Reader.id, Reader.email, ReaderSession.expires_at, ReaderSession.last_used_at
                )
                .join(Reader, Reader.id == ReaderSession.reader_id)
                .where(ReaderSession.token_digest == session_digest, ReaderSession.expires_at > now)
            )
        ).one_or_none()
    return SessionReader(*row) if row else None


async def renew_session(
    engine: AsyncEngine, session_digest: str, reader_id: int, expires_at: datetime, now: datetime
) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            update(ReaderSession)
            .where(ReaderSession.token_digest == session_digest)
            .values(expires_at=expires_at, last_used_at=now)
        )
        await connection.execute(
            update(Reader).where(Reader.id == reader_id).values(last_seen_at=now)
        )


async def end_session(engine: AsyncEngine, session_digest: str) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            delete(ReaderSession).where(ReaderSession.token_digest == session_digest)
        )


async def delete_reader(engine: AsyncEngine, reader_id: int) -> None:
    """The reader, their sessions and topics (by cascade) and every code sent to them."""
    async with engine.begin() as connection:
        email = (
            await connection.execute(
                delete(Reader).where(Reader.id == reader_id).returning(Reader.email)
            )
        ).scalar_one_or_none()
        if email is not None:
            await connection.execute(delete(SignInCode).where(SignInCode.email == email))


async def purge_expired(engine: AsyncEngine, now: datetime) -> None:
    async with engine.begin() as connection:
        await connection.execute(delete(SignInCode).where(SignInCode.expires_at <= now))
        await connection.execute(delete(ReaderSession).where(ReaderSession.expires_at <= now))


async def followed_topics(engine: AsyncEngine, reader_id: int) -> list[FollowedTopic]:
    async with engine.connect() as connection:
        rows = await connection.execute(
            select(Topic.slug, ReaderTopic.slot)
            .join(Topic, Topic.id == ReaderTopic.topic_id)
            .where(ReaderTopic.reader_id == reader_id)
            .order_by(ReaderTopic.slot)
        )
        return [FollowedTopic(*row) for row in rows]


async def set_followed_topics(
    engine: AsyncEngine, reader_id: int, topics: list[FollowedTopic]
) -> list[str]:
    """Replace the reader's topics; the slugs that name no active topic are left out and
    returned."""
    async with engine.begin() as connection:
        found = await connection.execute(
            select(Topic.slug, Topic.id).where(
                Topic.slug.in_([t.slug for t in topics]), Topic.status == "active"
            )
        )
        ids = {slug: topic_id for slug, topic_id in found}
        await connection.execute(delete(ReaderTopic).where(ReaderTopic.reader_id == reader_id))
        kept = [t for t in topics if t.slug in ids]
        if kept:
            await connection.execute(
                insert(ReaderTopic),
                [{"reader_id": reader_id, "topic_id": ids[t.slug], "slot": t.slot} for t in kept],
            )
    return [t.slug for t in topics if t.slug not in ids]
