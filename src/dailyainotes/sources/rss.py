"""RSS and Atom feeds, with conditional requests, and feed discovery on a web page."""

from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin

import feedparser

from dailyainotes.sources.http import Http
from dailyainotes.sources.items import (
    FetchOutcome,
    RawItem,
    clean_lead,
    from_struct_time,
    html_to_text,
)

FEED_TYPES = {"application/rss+xml", "application/atom+xml"}


class NotAFeedError(Exception):
    """The URL answered, but not with RSS or Atom."""


async def fetch_feed(
    http: Http, url: str, *, etag: str | None = None, last_modified: str | None = None
) -> FetchOutcome:
    headers = {}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified
    response = await http.get(url, headers)
    if response.status_code == 304:
        return FetchOutcome([], etag, last_modified, not_modified=True)
    response.raise_for_status()
    return FetchOutcome(
        parse_feed(response.content, url),
        response.headers.get("ETag"),
        response.headers.get("Last-Modified"),
    )


def parse_feed(content: bytes, url: str) -> list[RawItem]:
    feed = feedparser.parse(content)
    # feedparser reads an HTML page as an empty feed without flagging it; only the
    # version tells them apart.
    if not feed.version:
        raise NotAFeedError(url)
    return [item for entry in feed.entries if (item := to_item(entry))]


def to_item(entry: Any) -> RawItem | None:
    link, title = entry.get("link"), entry.get("title")
    if not link or not title:
        return None
    return RawItem(
        url=link,
        title=html_to_text(title),
        lead=clean_lead(entry.get("summary", "")),
        published_at=from_struct_time(entry.get("published_parsed") or entry.get("updated_parsed")),
    )


class _FeedLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        rel = (values.get("rel") or "").lower().split()
        is_feed = tag == "link" and "alternate" in rel and values.get("type") in FEED_TYPES
        if is_feed and (href := values.get("href")):
            self.hrefs.append(href)


def discover_feeds(html: str, base_url: str) -> list[str]:
    """The feeds a page advertises with `<link rel="alternate">`, as absolute URLs."""
    parser = _FeedLinkParser()
    parser.feed(html)
    return [urljoin(base_url, href) for href in parser.hrefs]


def is_feed(content: bytes) -> bool:
    return bool(feedparser.parse(content).version)
