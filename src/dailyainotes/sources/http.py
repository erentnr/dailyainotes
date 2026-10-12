"""The one HTTP client for sources: it identifies itself and spaces out requests per host
(INTENT.md, Security: be a polite client)."""

import asyncio
import time
from importlib.metadata import version
from types import TracebackType
from typing import Self
from urllib.parse import urlsplit

import httpx2

USER_AGENT = f"DailyAINotes/{version('dailyainotes')} (+https://dailyainotes.com)"

# Seconds between two requests to one host. arXiv asks for one request every 3 seconds.
DEFAULT_INTERVAL = 1.0
HOST_INTERVALS = {"export.arxiv.org": 3.0}
# Longest wait we honour from a Retry-After header, and the wait when it is missing.
MAX_BACKOFF = 300.0
DEFAULT_BACKOFF = 60.0


class Http:
    def __init__(
        self,
        client: httpx2.AsyncClient,
        *,
        intervals: dict[str, float] | None = None,
        default_interval: float = DEFAULT_INTERVAL,
    ) -> None:
        self.client = client
        self._intervals = HOST_INTERVALS if intervals is None else intervals
        self._default_interval = default_interval
        self._next_allowed: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def get(self, url: str, headers: dict[str, str] | None = None) -> httpx2.Response:
        host = urlsplit(url).hostname or ""
        async with self._locks.setdefault(host, asyncio.Lock()):
            wait = self._next_allowed.get(host, 0.0) - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            try:
                response = await self.client.get(url, headers=headers)
            finally:
                interval = self._intervals.get(host, self._default_interval)
                self._next_allowed[host] = time.monotonic() + interval
            if response.status_code in (429, 503):
                self._next_allowed[host] = time.monotonic() + backoff(response)
            return response

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.client.aclose()


def backoff(response: httpx2.Response) -> float:
    value = response.headers.get("Retry-After", "")
    return min(float(value), MAX_BACKOFF) if value.isdigit() else DEFAULT_BACKOFF


def create_http(transport: httpx2.AsyncBaseTransport | None = None) -> Http:
    client = httpx2.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        timeout=15.0,
        follow_redirects=True,
        transport=transport,
    )
    return Http(client)
