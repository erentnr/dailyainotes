"""Reader accounts (ADR 0003): sign-in with a code or link sent by email, sessions, the topics a
reader follows, topic suggestions, and deleting an account. Reading never needs one; Ask does
(ADR 0004).

Codes and session tokens are stored only as digests. Sign-in emails are limited per address,
per IP and per day, below what Resend's free plan sends."""

import hmac
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

import structlog

from dailyainotes.db import accounts as db
from dailyainotes.db import suggestions as suggestions_db
from dailyainotes.db.asks import count_request
from dailyainotes.db.engine import AsyncEngine
from dailyainotes.domain.accounts import (
    CODE_LIFETIME,
    MAX_CODE_ATTEMPTS,
    MAX_OPEN_SUGGESTIONS,
    MAX_TOPICS,
    SESSION_LIFETIME,
    SESSION_RENEWAL,
    code_digest,
    digest,
    is_valid_email,
    new_code,
    new_token,
    normalize_email,
)
from dailyainotes.external.resend import Email

log = structlog.get_logger(__name__)

PER_EMAIL_PER_WINDOW = 3
EMAIL_WINDOW = timedelta(minutes=15)
PER_IP_PER_DAY = 10
# Resend's free plan sends 100 emails a day.
PER_DAY = 80


class SignInError(Exception):
    """Shown to the reader as it is."""


class SignInOffError(SignInError):
    pass


class InvalidEmailError(SignInError):
    pass


class BotCheckFailedError(SignInError):
    pass


class TooManyCodesError(SignInError):
    pass


class WrongCodeError(SignInError):
    pass


class CodeUsedUpError(SignInError):
    pass


class InvalidTopicsError(SignInError):
    pass


class TooManySuggestionsError(SignInError):
    pass


class Mailer(Protocol):
    async def send(self, email: Email) -> None: ...


class BotCheck(Protocol):
    async def passed(self, token: str, ip: str) -> bool: ...


@dataclass(frozen=True)
class AccountDeps:
    engine: AsyncEngine
    # None while sign-in is off (no Resend key).
    mailer: Mailer | None
    # None while Turnstile is not set up.
    bot_check: BotCheck | None
    site_url: str


@dataclass(frozen=True)
class Session:
    token: str
    expires_at: datetime
    reader_id: int
    email: str


@dataclass(frozen=True)
class SignedIn:
    reader_id: int
    email: str
    # A new expiry when this request renewed the session, so the cookie is renewed too.
    renewed_until: datetime | None


@dataclass(frozen=True)
class Followed:
    slug: str
    slot: int


async def send_code(
    deps: AccountDeps, email: str, *, ip: str, ip_hash: str, bot_token: str, now: datetime
) -> None:
    """Email a sign-in code and link to the address."""
    if deps.mailer is None:
        raise SignInOffError("Sign-in is not available yet.")
    email = normalize_email(email)
    if not is_valid_email(email):
        raise InvalidEmailError("That does not look like an email address.")
    if deps.bot_check is not None and not await deps.bot_check.passed(bot_token, ip):
        raise BotCheckFailedError("The check that you are not a bot failed. Try again.")
    if await db.codes_sent_since(deps.engine, email, now - EMAIL_WINDOW) >= PER_EMAIL_PER_WINDOW:
        raise TooManyCodesError(
            "Three codes went to this address in the last 15 minutes. Use the newest one, or "
            "wait a few minutes."
        )
    day = now.date()
    if await count_request(deps.engine, f"sign-in-ip:{ip_hash}", day) > PER_IP_PER_DAY:
        raise TooManyCodesError("Too many sign-in emails from here today. Try again tomorrow.")
    if await count_request(deps.engine, "sign-in", day) > PER_DAY:
        raise TooManyCodesError("Sign-in is busy today. Try again tomorrow.")
    code, link = new_code(), new_token()
    await db.save_code(
        deps.engine, email, code_digest(email, code), digest(link), now + CODE_LIFETIME
    )
    await deps.mailer.send(sign_in_email(email, code, f"{deps.site_url}/sign-in/link#{link}"))
    log.info("sign_in_code_sent")


def sign_in_email(to: str, code: str, link: str) -> Email:
    minutes = int(CODE_LIFETIME.total_seconds() // 60)
    text = (
        f"Your sign-in code for Daily AI Notes is {code}.\n\n"
        f"Or open this link on the device you are signing in on:\n{link}\n\n"
        f"The code and the link work once, for {minutes} minutes. If you did not ask to sign "
        "in, ignore this email; nothing changes.\n"
    )
    html = (
        '<div style="font-family:Georgia,serif;font-size:16px;line-height:1.5;color:#16171a">'
        f"<p>Your sign-in code for Daily AI Notes is</p>"
        f'<p style="font-family:monospace;font-size:28px;letter-spacing:4px">{code}</p>'
        f'<p>Or <a href="{link}">sign in with this link</a> on the device you are signing in '
        "on.</p>"
        f"<p>The code and the link work once, for {minutes} minutes. If you did not ask to sign "
        "in, ignore this email; nothing changes.</p></div>"
    )
    return Email(to=to, subject=f"{code} is your Daily AI Notes sign-in code", text=text, html=html)


async def sign_in_with_code(engine: AsyncEngine, email: str, code: str, now: datetime) -> Session:
    email = normalize_email(email)
    if not is_valid_email(email):
        raise InvalidEmailError("That does not look like an email address.")
    live = await db.spend_try(engine, email, now, MAX_CODE_ATTEMPTS)
    if live is None:
        raise CodeUsedUpError("That code has expired or was used. Ask for a new one.")
    if not hmac.compare_digest(live.code_digest, code_digest(email, code.strip())):
        left = MAX_CODE_ATTEMPTS - live.attempts
        if left == 0:
            raise CodeUsedUpError("Too many wrong codes. Ask for a new one.")
        raise WrongCodeError(
            f"That code is not right. {left} {'try' if left == 1 else 'tries'} left."
        )
    return await open_session(engine, email, now)


async def sign_in_with_link(engine: AsyncEngine, token: str, now: datetime) -> Session:
    email = await db.live_code_for_link(engine, digest(token), now, MAX_CODE_ATTEMPTS)
    if email is None:
        raise CodeUsedUpError("That link has expired or was used. Ask for a new code.")
    return await open_session(engine, email, now)


async def open_session(engine: AsyncEngine, email: str, now: datetime) -> Session:
    token = new_token()
    expires_at = now + SESSION_LIFETIME
    reader_id = await db.sign_in(engine, email, digest(token), expires_at, now)
    log.info("reader_signed_in", reader_id=reader_id)
    return Session(token, expires_at, reader_id, email)


async def signed_in(engine: AsyncEngine, token: str, now: datetime) -> SignedIn | None:
    """The reader a session token belongs to, renewing the session once a day of use."""
    found = await db.session_reader(engine, digest(token), now)
    if found is None:
        return None
    renewed_until = None
    if now - found.last_used_at >= SESSION_RENEWAL:
        renewed_until = now + SESSION_LIFETIME
        await db.renew_session(engine, digest(token), found.id, renewed_until, now)
    return SignedIn(found.id, found.email, renewed_until)


async def sign_out(engine: AsyncEngine, token: str) -> None:
    await db.end_session(engine, digest(token))


async def followed(engine: AsyncEngine, reader_id: int) -> list[Followed]:
    return [Followed(t.slug, t.slot) for t in await db.followed_topics(engine, reader_id)]


async def follow(engine: AsyncEngine, reader_id: int, topics: list[Followed]) -> list[Followed]:
    """Replace the topics the reader follows; topics no longer active are dropped."""
    slugs, slots = [t.slug for t in topics], [t.slot for t in topics]
    if len(topics) > MAX_TOPICS or len(set(slugs)) < len(slugs) or len(set(slots)) < len(slots):
        raise InvalidTopicsError(f"Follow at most {MAX_TOPICS} topics, each in its own slot.")
    await db.set_followed_topics(
        engine, reader_id, [db.FollowedTopic(t.slug, t.slot) for t in topics]
    )
    return await followed(engine, reader_id)


async def delete_account(engine: AsyncEngine, reader_id: int) -> None:
    await db.delete_reader(engine, reader_id)
    log.info("reader_deleted", reader_id=reader_id)


async def purge_expired(engine: AsyncEngine, now: datetime) -> None:
    await db.purge_expired(engine, now)


async def suggest(engine: AsyncEngine, reader_id: int, name: str, note: str) -> None:
    """A topic suggestion for the editor; a reader has a few waiting at most."""
    if await suggestions_db.open_count(engine, reader_id) >= MAX_OPEN_SUGGESTIONS:
        raise TooManySuggestionsError(
            f"You have {MAX_OPEN_SUGGESTIONS} suggestions waiting for the editor. Suggest another "
            "once one is answered."
        )
    await suggestions_db.add(engine, reader_id, " ".join(name.split()), note.strip())
    log.info("topic_suggested", reader_id=reader_id)


async def suggestions(engine: AsyncEngine, reader_id: int) -> list[suggestions_db.ReaderSuggestion]:
    return await suggestions_db.for_reader(engine, reader_id)


async def accept_suggestion(
    engine: AsyncEngine,
    suggestion_id: int,
    by: str,
    queue_plan: Callable[[str], Awaitable[None]],
) -> str:
    """The editor accepts: a draft topic is made, and the worker runs the Topic Planner on it.
    The new topic's slug."""
    slug = await suggestions_db.accept(engine, suggestion_id, by)
    await queue_plan(slug)
    log.info("suggestion_accepted", suggestion=suggestion_id, topic=slug)
    return slug


async def decline_suggestion(engine: AsyncEngine, suggestion_id: int, reason: str, by: str) -> None:
    await suggestions_db.decline(engine, suggestion_id, reason.strip(), by)
