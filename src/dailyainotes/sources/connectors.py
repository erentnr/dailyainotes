"""Pick the connector for a source row."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from dailyainotes.sources.arxiv import fetch_arxiv
from dailyainotes.sources.github import fetch_github_releases
from dailyainotes.sources.hackernews import fetch_hackernews
from dailyainotes.sources.http import Http
from dailyainotes.sources.items import FetchOutcome
from dailyainotes.sources.rss import fetch_feed

# How far back a search-style source (Hacker News) looks on each run.
SEARCH_WINDOW = timedelta(days=3)


@dataclass(frozen=True)
class SourceSpec:
    type: str
    locator: str
    config: dict[str, Any]
    etag: str | None = None
    last_modified: str | None = None


async def fetch_source(
    http: Http, source: SourceSpec, *, now: datetime, github_token: str | None = None
) -> FetchOutcome:
    match source.type:
        case "rss":
            return await fetch_feed(
                http, source.locator, etag=source.etag, last_modified=source.last_modified
            )
        case "arxiv":
            return await fetch_arxiv(http, source.locator)
        case "github_releases":
            return await fetch_github_releases(http, source.locator, token=github_token)
        case "hackernews":
            return await fetch_hackernews(
                http,
                source.locator,
                min_points=source.config.get("min_points", 50),
                since=now - SEARCH_WINDOW,
            )
    raise ValueError(f"unknown source type {source.type!r}")
