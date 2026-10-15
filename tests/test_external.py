"""Resend and Turnstile, against responses shaped like their documented ones
(tests/fixtures/resend, tests/fixtures/turnstile)."""

import json
from collections.abc import Callable

import httpx2
import pytest

from dailyainotes.external.resend import Email, EmailNotSentError, ResendMailer
from dailyainotes.external.turnstile import TurnstileCheck

pytestmark = pytest.mark.anyio

EMAIL = Email(to="reader@example.com", subject="123456 is your code", text="t", html="<p>h</p>")


def serving(status: int, body: bytes, seen: list[httpx2.Request]) -> httpx2.AsyncClient:
    def handle(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return httpx2.Response(status, content=body, headers={"content-type": "application/json"})

    return httpx2.AsyncClient(transport=httpx2.MockTransport(handle))


async def test_an_email_goes_to_resend_with_the_key_and_both_bodies(
    fixture: Callable[[str], bytes],
) -> None:
    seen: list[httpx2.Request] = []
    mailer = ResendMailer(
        serving(200, fixture("resend/sent.json"), seen), "re_test", "DAN <s@x.io>"
    )

    await mailer.send(EMAIL)

    (request,) = seen
    assert str(request.url) == "https://api.resend.com/emails"
    assert request.headers["authorization"] == "Bearer re_test"
    assert json.loads(request.content) == {
        "from": "DAN <s@x.io>",
        "to": ["reader@example.com"],
        "subject": "123456 is your code",
        "text": "t",
        "html": "<p>h</p>",
    }


async def test_a_refused_email_raises_with_resends_reason(fixture: Callable[[str], bytes]) -> None:
    body = fixture("resend/domain-not-verified.json")
    mailer = ResendMailer(serving(403, body, []), "re_test", "DAN <s@x.io>")

    with pytest.raises(EmailNotSentError, match=r"403.*not verified"):
        await mailer.send(EMAIL)


async def test_resend_out_of_reach_raises() -> None:
    def fail(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("down", request=request)

    client = httpx2.AsyncClient(transport=httpx2.MockTransport(fail))

    with pytest.raises(EmailNotSentError, match="ConnectError"):
        await ResendMailer(client, "re_test", "DAN <s@x.io>").send(EMAIL)


@pytest.mark.parametrize(
    ("name", "hostname", "passed"),
    [
        ("turnstile/passed.json", "dailyainotes.com", True),
        # Solved on someone else's site with our public site key.
        ("turnstile/passed.json", "other.example", False),
        ("turnstile/duplicate.json", "dailyainotes.com", False),
    ],
)
async def test_turnstile_passes_only_a_fresh_token_solved_on_our_site(
    fixture: Callable[[str], bytes], name: str, hostname: str, passed: bool
) -> None:
    seen: list[httpx2.Request] = []
    check = TurnstileCheck(serving(200, fixture(name), seen), "secret", hostname)

    assert await check.passed("token-from-widget", "203.0.113.7") is passed
    (request,) = seen
    assert request.content == b"secret=secret&response=token-from-widget&remoteip=203.0.113.7"


async def test_turnstile_fails_closed() -> None:
    seen: list[httpx2.Request] = []
    garbled = TurnstileCheck(serving(500, b"<html>", seen), "secret", "dailyainotes.com")
    empty = TurnstileCheck(serving(200, b"{}", seen), "secret", "dailyainotes.com")

    assert await garbled.passed("token", "203.0.113.7") is False
    assert await empty.passed("", "203.0.113.7") is False
    assert len(seen) == 1  # an empty token is refused without asking
