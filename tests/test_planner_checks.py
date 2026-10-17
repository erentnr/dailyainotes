from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pytest

from dailyainotes.graphs.topic_planner import check, drop_reason, feed_source

pytestmark = pytest.mark.anyio

FEED = "https://news.example.com/feed/"
NOW = datetime(2026, 10, 12, 18, tzinfo=UTC)


class BrokenFetcher:
    async def decide(self, url: str, **_: Any) -> Any:
        raise ValueError(f"unknown url type: {url!r}")


async def test_a_feed_whose_pages_cannot_be_checked_counts_as_unreadable(
    web: Callable[..., Any], fixture: Callable[[str], bytes]
) -> None:
    http = web({FEED: fixture("rss/feed.xml")}).http

    checked = await check(
        http,
        BrokenFetcher(),  # type: ignore[arg-type]
        feed_source(FEED),
        ["safety car"],
        NOW,
        None,
    )

    assert checked["readable_share"] == 0.0
    assert drop_reason(checked) == (
        "its pages are link-only: its pages could not be checked (ValueError)"
    )
