"""The policy gate: every web page fetch goes through `ArticleFetcher.decide`
(INTENT.md, Architectural Constraints)."""

import time
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlsplit

import httpx2
import structlog
import trafilatura

from dailyainotes.domain.exclusions import is_excluded
from dailyainotes.sources.http import Http
from dailyainotes.sources.policy import (
    RobotsPolicy,
    allow_all,
    deny_all,
    header_opt_out,
    page_opt_out,
    parse_robots,
)
from dailyainotes.sources.urls import registrable_domain

log = structlog.get_logger(__name__)

TextPolicy = Literal["full", "summary", "link_only"]

# RFC 9309: cache robots.txt for at most 24 hours.
ROBOTS_TTL = 24 * 60 * 60
# Less extracted text than this is a teaser, a script-rendered page or a paywall.
MIN_ARTICLE_CHARACTERS = 500


@dataclass(frozen=True)
class PageDecision:
    text_policy: TextPolicy
    reason: str
    # The extracted article text, only for `full`.
    content: str | None = None


class ArticleFetcher:
    def __init__(self, http: Http) -> None:
        self.http = http
        self._robots: dict[str, tuple[float, RobotsPolicy]] = {}

    async def decide(self, url: str, *, publisher_paywalled: bool = False) -> PageDecision:
        if is_excluded(registrable_domain(url)):
            return PageDecision("link_only", "excluded publisher")
        if publisher_paywalled:
            return PageDecision("link_only", "publisher is paywalled")
        robots = await self.robots(url)
        if robots.opt_out:
            return PageDecision("link_only", robots.opt_out)
        if not robots.allows(url):
            return PageDecision("link_only", "robots.txt disallows us")
        try:
            response = await self.http.get(url)
        except httpx2.HTTPError as error:
            return PageDecision("summary", f"page unreachable: {type(error).__name__}")
        if response.status_code in (401, 402, 403):
            return PageDecision("link_only", f"access restricted ({response.status_code})")
        if response.status_code >= 400:
            return PageDecision("summary", f"page returned {response.status_code}")
        if reason := header_opt_out(dict(response.headers)):
            return PageDecision("link_only", reason)
        if "html" not in response.headers.get("content-type", "html"):
            return PageDecision("summary", "not an HTML page")
        html = response.text
        if reason := page_opt_out(html):
            return PageDecision("link_only", reason)
        text = trafilatura.extract(html, url=url, favor_precision=True) or ""
        if len(text) < MIN_ARTICLE_CHARACTERS:
            return PageDecision("summary", "too little article text")
        return PageDecision("full", "allowed", text)

    async def robots(self, url: str) -> RobotsPolicy:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        cached = self._robots.get(origin)
        if cached and time.monotonic() - cached[0] < ROBOTS_TTL:
            return cached[1]
        policy = await self._fetch_robots(origin)
        self._robots[origin] = (time.monotonic(), policy)
        return policy

    async def _fetch_robots(self, origin: str) -> RobotsPolicy:
        try:
            response = await self.http.get(f"{origin}/robots.txt")
        except httpx2.HTTPError as error:
            log.info("robots_unreachable", origin=origin, error=type(error).__name__)
            return deny_all("robots.txt unreachable")
        # RFC 9309: a 4xx means no rules; a 5xx means assume everything is disallowed.
        if 400 <= response.status_code < 500:
            return allow_all()
        if response.status_code >= 500:
            return deny_all(f"robots.txt returned {response.status_code}")
        return parse_robots(response.text)
