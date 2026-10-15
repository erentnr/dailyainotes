"""Reader accounts (ADR 0003): sign-in by an emailed code or link, sessions, limits, the topics a
reader follows, and deleting an account. Exhaustive, as sign-in guards readers' data."""

import re
from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx2
import pytest
from sqlalchemy import func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncEngine

from dailyainotes import accounts
from dailyainotes.accounts import AccountDeps
from dailyainotes.api.accounts import COOKIE
from dailyainotes.api.app import create_app
from dailyainotes.db.tables import Reader, ReaderSession, ReaderTopic, SignInCode, Topic
from dailyainotes.external.resend import Email, EmailNotSentError
from dailyainotes.settings import Settings

pytestmark = [pytest.mark.integration, pytest.mark.anyio]

SITE = "http://test"
READER = "reader@example.com"


class Mailbox:
    """Stands in for Resend and keeps what was sent."""

    def __init__(self) -> None:
        self.sent: list[Email] = []

    async def send(self, email: Email) -> None:
        self.sent.append(email)

    def code(self) -> str:
        match = re.search(r"is (\d{6})\.", self.sent[-1].text)
        assert match, self.sent[-1].text
        return match.group(1)

    def link_token(self) -> str:
        match = re.search(r"/sign-in/link#(\S+)", self.sent[-1].text)
        assert match, self.sent[-1].text
        return match.group(1)


class Bot:
    def __init__(self, passes: bool) -> None:
        self.passes = passes
        self.asked: list[tuple[str, str]] = []

    async def passed(self, token: str, ip: str) -> bool:
        self.asked.append((token, ip))
        return self.passes


@pytest.fixture
def mailbox() -> Mailbox:
    return Mailbox()


@pytest.fixture
def deps(engine: AsyncEngine, mailbox: Mailbox) -> AccountDeps:
    return AccountDeps(engine, mailbox, None, SITE)


@pytest.fixture
async def site(engine: AsyncEngine, deps: AccountDeps) -> AsyncIterator[httpx2.AsyncClient]:
    async with client_for(engine, deps) as client:
        yield client


def client_for(engine: AsyncEngine, deps: AccountDeps, *, site_url: str = SITE) -> Any:
    app = create_app(Settings(_env_file=None, site_url=site_url, turnstile_site_key="site-key"))
    app.state.engine = engine  # ASGITransport does not run the lifespan
    app.state.accounts = deps
    return httpx2.AsyncClient(
        transport=httpx2.ASGITransport(app=app), base_url=SITE, headers={"Origin": SITE}
    )


async def signed_in_reader(site: httpx2.AsyncClient, mailbox: Mailbox, email: str = READER) -> Any:
    assert (await site.post("/api/v1/auth/code", json={"email": email})).status_code == 202
    response = await site.post("/api/v1/auth/verify", json={"email": email, "code": mailbox.code()})
    assert response.status_code == 200, response.text
    return response


async def rows(engine: AsyncEngine, table: Any) -> int:
    async with engine.connect() as connection:
        count: int = (
            await connection.execute(select(func.count()).select_from(table))
        ).scalar_one()
    return count


async def add_topics(engine: AsyncEngine, *slugs: str, status: str = "active") -> None:
    async with engine.begin() as connection:
        await connection.execute(
            insert(Topic),
            [{"slug": s, "name": s.title(), "description": "", "status": status} for s in slugs],
        )


async def test_a_reader_signs_in_with_the_emailed_code(
    site: httpx2.AsyncClient, mailbox: Mailbox
) -> None:
    anonymous = (await site.get("/api/v1/me")).json()
    sent = await site.post("/api/v1/auth/code", json={"email": "  Reader@Example.com "})

    signed = await site.post("/api/v1/auth/verify", json={"email": READER, "code": mailbox.code()})
    me = (await site.get("/api/v1/me")).json()

    assert anonymous is None
    assert sent.status_code == 202
    (email,) = mailbox.sent
    assert email.to == READER
    assert email.subject == f"{mailbox.code()} is your Daily AI Notes sign-in code"
    assert f"{SITE}/sign-in/link#" in email.html
    assert signed.json() == {"email": READER, "topics": []}
    cookie = signed.headers["set-cookie"]
    assert cookie.startswith(f"{COOKIE}=")
    for flag in ("HttpOnly", "SameSite=lax", "Max-Age=2592000"):
        assert flag in cookie
    assert me == {"email": READER, "topics": []}


async def test_the_link_signs_in_too_and_either_works_only_once(
    site: httpx2.AsyncClient, mailbox: Mailbox
) -> None:
    await site.post("/api/v1/auth/code", json={"email": READER})
    code, token = mailbox.code(), mailbox.link_token()

    by_link = await site.post("/api/v1/auth/link", json={"token": token})
    link_again = await site.post("/api/v1/auth/link", json={"token": token})
    code_after = await site.post("/api/v1/auth/verify", json={"email": READER, "code": code})

    assert by_link.json()["email"] == READER
    assert link_again.status_code == code_after.status_code == 400
    assert "expired or was used" in code_after.json()["detail"]


async def test_codes_and_tokens_are_stored_only_as_digests(
    engine: AsyncEngine, site: httpx2.AsyncClient, mailbox: Mailbox
) -> None:
    response = await signed_in_reader(site, mailbox)
    session_token = response.cookies[COOKIE]

    async with engine.connect() as connection:
        stored = str((await connection.execute(select(SignInCode))).all())
        stored += str((await connection.execute(select(ReaderSession))).all())

    for secret in (mailbox.code(), mailbox.link_token(), session_token):
        assert secret not in stored


async def test_five_wrong_codes_void_the_code_and_its_link(
    site: httpx2.AsyncClient, mailbox: Mailbox
) -> None:
    await site.post("/api/v1/auth/code", json={"email": READER})
    right = mailbox.code()
    wrong = "000000" if right != "000000" else "111111"

    answers = [
        (await site.post("/api/v1/auth/verify", json={"email": READER, "code": wrong})).json()
        for _ in range(5)
    ]
    right_after = await site.post("/api/v1/auth/verify", json={"email": READER, "code": right})
    link_after = await site.post("/api/v1/auth/link", json={"token": mailbox.link_token()})

    assert answers[0]["detail"] == "That code is not right. 4 tries left."
    assert answers[3]["detail"] == "That code is not right. 1 try left."
    assert answers[4]["detail"] == "Too many wrong codes. Ask for a new one."
    assert right_after.status_code == link_after.status_code == 400


async def test_a_code_expires_after_ten_minutes(
    engine: AsyncEngine, deps: AccountDeps, mailbox: Mailbox
) -> None:
    now = datetime.now(UTC)
    await accounts.send_code(deps, READER, ip="203.0.113.7", ip_hash="h", bot_token="", now=now)
    code = mailbox.code()

    with pytest.raises(accounts.CodeUsedUpError):
        await accounts.sign_in_with_code(engine, READER, code, now + timedelta(minutes=11))
    session = await accounts.sign_in_with_code(engine, READER, code, now + timedelta(minutes=9))
    assert session.email == READER


async def test_sign_in_emails_are_limited_per_address_per_ip_and_per_day(
    engine: AsyncEngine, deps: AccountDeps, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime.now(UTC)

    async def send(email: str, ip_hash: str = "ip-a", at: datetime = now) -> None:
        await accounts.send_code(deps, email, ip="1.2.3.4", ip_hash=ip_hash, bot_token="", now=at)

    for _ in range(3):
        await send(READER)
    with pytest.raises(accounts.TooManyCodesError, match="last 15 minutes"):
        await send(READER)
    await send(READER, at=now + timedelta(minutes=16))  # a new window

    for n in range(6):  # ten from ip-a in all, counting the four above
        await send(f"reader{n}@example.com")
    with pytest.raises(accounts.TooManyCodesError, match="from here today"):
        await send("one-more@example.com")

    # Ten went out today; the next is the eleventh, then the day is full.
    monkeypatch.setattr(accounts, "PER_DAY", 11)
    await send("elsewhere@example.com", ip_hash="ip-b")
    with pytest.raises(accounts.TooManyCodesError, match="busy today"):
        await send("elsewhere2@example.com", ip_hash="ip-b")


async def test_the_bot_check_runs_before_anything_is_sent(
    engine: AsyncEngine, deps: AccountDeps, mailbox: Mailbox
) -> None:
    bot = Bot(passes=False)
    async with client_for(engine, replace(deps, bot_check=bot)) as site:
        refused = await site.post(
            "/api/v1/auth/code", json={"email": READER, "bot_token": "widget-token"}
        )

    assert refused.status_code == 400
    assert "not a bot" in refused.json()["detail"]
    assert bot.asked == [("widget-token", "127.0.0.1")]
    assert mailbox.sent == []
    assert await rows(engine, SignInCode) == 0


async def test_requests_that_change_an_account_must_come_from_the_site(
    site: httpx2.AsyncClient, mailbox: Mailbox
) -> None:
    elsewhere = {"Origin": "https://evil.example"}

    send = await site.post("/api/v1/auth/code", json={"email": READER}, headers=elsewhere)
    await signed_in_reader(site, mailbox)
    topics = await site.put("/api/v1/me/topics", json={"topics": []}, headers=elsewhere)
    delete = await site.delete("/api/v1/me", headers=elsewhere)
    del site.headers["Origin"]
    no_origin = await site.post("/api/v1/auth/sign-out")

    assert [r.status_code for r in (send, topics, delete, no_origin)] == [403] * 4
    assert (await site.get("/api/v1/me")).json()["email"] == READER


async def test_signing_out_ends_the_session(site: httpx2.AsyncClient, mailbox: Mailbox) -> None:
    response = await signed_in_reader(site, mailbox)
    token = response.cookies[COOKIE]

    out = await site.post("/api/v1/auth/sign-out")
    site.cookies.set(COOKIE, token)  # the old cookie, kept by someone

    assert out.status_code == 204
    assert (await site.get("/api/v1/me")).json() is None


async def test_a_session_lasts_thirty_days_and_renews_once_a_day_of_use(
    engine: AsyncEngine, deps: AccountDeps
) -> None:
    now = datetime.now(UTC)
    session = await accounts.open_session(engine, READER, now)

    same_day = await accounts.signed_in(engine, session.token, now + timedelta(hours=3))
    next_day = await accounts.signed_in(engine, session.token, now + timedelta(days=2))
    later = await accounts.signed_in(engine, session.token, now + timedelta(days=31))
    unused = await accounts.signed_in(engine, session.token, now + timedelta(days=63))

    assert same_day is not None
    assert same_day.renewed_until is None
    assert next_day is not None
    assert next_day.renewed_until == now + timedelta(days=32)
    assert later is not None  # renewed on day 2, so valid until day 32
    assert unused is None


async def test_a_reader_follows_active_topics_in_their_slots(
    engine: AsyncEngine, site: httpx2.AsyncClient, mailbox: Mailbox
) -> None:
    await add_topics(engine, "formula-1", "astronomy")
    await add_topics(engine, "tennis", status="draft")
    await signed_in_reader(site, mailbox)

    saved = await site.put(
        "/api/v1/me/topics",
        json={
            "topics": [
                {"slug": "astronomy", "slot": 3},
                {"slug": "formula-1", "slot": 1},
                {"slug": "tennis", "slot": 2},
            ]
        },
    )
    twice = await site.put(
        "/api/v1/me/topics",
        json={"topics": [{"slug": "astronomy", "slot": 1}, {"slug": "astronomy", "slot": 2}]},
    )
    too_many = await site.put(
        "/api/v1/me/topics",
        json={"topics": [{"slug": f"t{n}", "slot": n % 8 + 1} for n in range(9)]},
    )

    assert saved.json()["topics"] == [
        {"slug": "formula-1", "slot": 1},
        {"slug": "astronomy", "slot": 3},
    ]
    assert twice.status_code == 400
    assert too_many.status_code == 422
    assert (await site.get("/api/v1/me")).json()["topics"] == saved.json()["topics"]


async def test_topics_need_a_signed_in_reader(site: httpx2.AsyncClient) -> None:
    response = await site.put("/api/v1/me/topics", json={"topics": []})

    assert response.status_code == 401


async def test_deleting_an_account_removes_every_row_about_the_reader(
    engine: AsyncEngine, site: httpx2.AsyncClient, mailbox: Mailbox
) -> None:
    await add_topics(engine, "formula-1")
    await signed_in_reader(site, mailbox)
    await site.put("/api/v1/me/topics", json={"topics": [{"slug": "formula-1", "slot": 1}]})
    await site.post("/api/v1/auth/code", json={"email": READER})  # one more code, unused
    await signed_in_reader(site, mailbox, "other@example.com")
    await site.post("/api/v1/auth/sign-out")
    await signed_in_reader(site, mailbox)

    deleted = await site.delete("/api/v1/me")

    assert deleted.status_code == 204
    assert (await site.get("/api/v1/me")).json() is None
    async with engine.connect() as connection:
        emails = (await connection.execute(select(Reader.email))).scalars().all()
        code_emails = set((await connection.execute(select(SignInCode.email))).scalars())
    assert emails == ["other@example.com"]
    assert code_emails == {"other@example.com"}
    assert await rows(engine, ReaderTopic) == 0
    # The deleted reader's two sessions went with them; the other reader signed out.
    assert await rows(engine, ReaderSession) == 0


async def test_sign_in_is_off_without_a_mailer_and_a_failed_send_says_so(
    engine: AsyncEngine, deps: AccountDeps
) -> None:
    class Down:
        async def send(self, email: Email) -> None:
            raise EmailNotSentError("Resend answered 500")

    async with client_for(engine, replace(deps, mailer=None)) as off:
        options = (await off.get("/api/v1/auth/options")).json()
        refused = await off.post("/api/v1/auth/code", json={"email": READER})
    async with client_for(engine, replace(deps, mailer=Down())) as down:
        failed = await down.post("/api/v1/auth/code", json={"email": READER})

    assert options == {"sign_in": False, "turnstile_site_key": "site-key"}
    assert refused.status_code == 503
    assert failed.status_code == 502


async def test_the_cookie_is_secure_on_https(engine: AsyncEngine, mailbox: Mailbox) -> None:
    deps = AccountDeps(engine, mailbox, None, "https://dailyainotes.com")
    async with client_for(engine, deps, site_url="https://dailyainotes.com") as site:
        site.headers["Origin"] = "https://dailyainotes.com"
        await site.post("/api/v1/auth/code", json={"email": READER})
        response = await site.post(
            "/api/v1/auth/verify", json={"email": READER, "code": mailbox.code()}
        )

    assert "Secure" in response.headers["set-cookie"]


async def test_expired_codes_and_sessions_are_purged(
    engine: AsyncEngine, deps: AccountDeps
) -> None:
    now = datetime.now(UTC)
    await accounts.send_code(deps, READER, ip="1.2.3.4", ip_hash="h", bot_token="", now=now)
    await accounts.open_session(engine, READER, now)
    async with engine.begin() as connection:
        await connection.execute(update(ReaderSession).values(expires_at=now - timedelta(days=1)))

    await accounts.purge_expired(engine, now + timedelta(minutes=11))

    assert await rows(engine, SignInCode) == 0
    assert await rows(engine, ReaderSession) == 0
    assert await rows(engine, Reader) == 1
