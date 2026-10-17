from collections.abc import Callable
from typing import Any

import pytest

from dailyainotes.graphs.topic_planner import one_site
from dailyainotes.sources.fetcher import ArticleFetcher

pytestmark = pytest.mark.anyio

SITE = "https://news.example.com/"
HTML = {"Content-Type": "text/html"}


async def test_a_guessed_feed_address_that_fails_falls_back_to_the_home_page(
    web: Callable[..., Any], fixture: Callable[[str], bytes]
) -> None:
    """Found 2026-10-16: 11 of the 27 addresses the model guessed for video games answered 404."""
    recorded = web(
        {
            f"{SITE}robots.txt": (404, b"", {}),
            f"{SITE}games/rss/index.xml": (404, b"", {}),
            # The home page links its feed the usual way.
            SITE: (
                200,
                fixture("rss/homepage.html").replace(
                    b"https://lab.example.org", SITE.rstrip("/").encode()
                ),
                HTML,
            ),
        }
    )

    feeds, reason = await one_site(
        recorded.http, ArticleFetcher(recorded.http), f"{SITE}games/rss/index.xml"
    )

    assert feeds == [f"{SITE}blog/feed.xml", f"{SITE}atom.xml"]
    assert reason == ""


async def test_a_site_that_links_no_feed_is_tried_at_the_usual_feed_paths(
    web: Callable[..., Any], fixture: Callable[[str], bytes]
) -> None:
    recorded = web(
        {
            f"{SITE}robots.txt": (404, b"", {}),
            f"{SITE}rss": fixture("rss/feed.xml"),
            SITE: (200, b"<html><body>No feed link</body></html>", HTML),
        }
    )

    feeds, _ = await one_site(recorded.http, ArticleFetcher(recorded.http), SITE)

    assert feeds == [f"{SITE}rss"]
    # The usual paths stop at the first feed: /feed first, then /rss.
    tried = [str(r.url) for r in recorded.requests if not str(r.url).endswith("robots.txt")]
    assert tried == [SITE, f"{SITE}feed", f"{SITE}rss"]


async def test_a_site_without_any_feed_keeps_the_first_reason(web: Callable[..., Any]) -> None:
    recorded = web(
        {
            f"{SITE}robots.txt": (404, b"", {}),
            SITE: (200, b"<html><body>No feed link</body></html>", HTML),
        }
    )

    feeds, reason = await one_site(recorded.http, ArticleFetcher(recorded.http), SITE)

    assert (feeds, reason) == ([], "advertises no feed, nor serves one at the usual paths")


async def test_the_usual_paths_are_not_tried_where_robots_txt_disallows_us(
    web: Callable[..., Any],
) -> None:
    recorded = web({f"{SITE}robots.txt": b"User-agent: *\nDisallow: /\n"})

    feeds, reason = await one_site(recorded.http, ArticleFetcher(recorded.http), SITE)

    assert (feeds, reason) == ([], "its robots.txt disallows us")
    assert [str(r.url) for r in recorded.requests] == [f"{SITE}robots.txt"]
