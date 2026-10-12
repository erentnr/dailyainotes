import time

import httpx2
import pytest

from dailyainotes.sources.http import USER_AGENT, Http, backoff, create_http

pytestmark = pytest.mark.anyio


async def test_requests_to_one_host_are_spaced_out() -> None:
    client = httpx2.AsyncClient(transport=httpx2.MockTransport(lambda _: httpx2.Response(200)))
    http = Http(client, intervals={"a.example": 0.2}, default_interval=0)

    start = time.monotonic()
    await http.get("https://a.example/1")
    await http.get("https://a.example/2")
    await http.get("https://b.example/1")

    assert 0.2 <= time.monotonic() - start < 0.4


def test_backoff_honours_retry_after_up_to_a_limit() -> None:
    assert backoff(httpx2.Response(429, headers={"Retry-After": "12"})) == 12
    assert backoff(httpx2.Response(429, headers={"Retry-After": "99999"})) == 300
    assert backoff(httpx2.Response(503)) == 60


async def test_the_client_identifies_itself() -> None:
    seen: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return httpx2.Response(200)

    async with create_http(transport=httpx2.MockTransport(handler)) as http:
        await http.get("https://a.example/")

    assert seen[0].headers["User-Agent"] == USER_AGENT
    assert USER_AGENT.startswith("DailyAINotes/")
