from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest

from dailyainotes.sources.arxiv import fetch_arxiv
from dailyainotes.sources.connectors import SourceSpec, fetch_source
from dailyainotes.sources.github import fetch_github_releases
from dailyainotes.sources.hackernews import fetch_hackernews
from dailyainotes.sources.rss import NotAFeedError, discover_feeds, fetch_feed

pytestmark = pytest.mark.anyio

Fixture = Callable[[str], bytes]
Web = Callable[[dict[str, Any]], Any]
FEED = "https://news.example.com/feed/"
NOW = datetime(2026, 10, 12, 12, tzinfo=UTC)


async def test_an_rss_feed_becomes_plain_text_items(fixture: Fixture, web: Web) -> None:
    outcome = await fetch_feed(web({FEED: fixture("rss/feed.xml")}).http, FEED)

    first, second, undated = outcome.items
    assert first.title == "“Late safety car” decides a wet race | Formula 1"
    assert first.lead == "A late safety car and a strategy gamble decided the race."
    assert first.published_at == datetime(2026, 10, 12, 14, 49, 15, tzinfo=UTC)
    assert second.lead == "A new power unit means a grid drop for one driver."
    assert undated.published_at is None


async def test_relative_item_links_are_read_against_the_feed_url(
    fixture: Fixture, web: Web
) -> None:
    (item,) = (await fetch_feed(web({FEED: fixture("rss/relative-links.xml")}).http, FEED)).items

    assert item.url == "https://news.example.com/article/151036/an-update-adds-a-character-respec"


async def test_a_feed_is_fetched_conditionally_and_304_means_no_items(web: Web) -> None:
    recorded = web({FEED: (304, b"", {})})

    outcome = await fetch_feed(recorded.http, FEED, etag='"v1"', last_modified="Mon, 12 Oct")

    assert outcome.not_modified
    assert outcome.items == []
    request = recorded.requests[0]
    assert request.headers["If-None-Match"] == '"v1"'
    assert request.headers["If-Modified-Since"] == "Mon, 12 Oct"


async def test_a_feed_response_carries_its_validators_for_next_time(
    fixture: Fixture, web: Web
) -> None:
    headers = {"ETag": '"v2"', "Last-Modified": "Tue, 13 Oct 2026 08:00:00 GMT"}
    recorded = web({FEED: (200, fixture("rss/feed.xml"), headers)})

    outcome = await fetch_feed(recorded.http, FEED)

    assert (outcome.etag, outcome.last_modified) == ('"v2"', "Tue, 13 Oct 2026 08:00:00 GMT")


async def test_an_html_page_is_not_mistaken_for_an_empty_feed(fixture: Fixture, web: Web) -> None:
    with pytest.raises(NotAFeedError):
        await fetch_feed(web({FEED: fixture("rss/homepage.html")}).http, FEED)


async def test_an_atom_feed_is_read_too(fixture: Fixture, web: Web) -> None:
    url = "https://lab.example.org/atom.xml"

    (item,) = (await fetch_feed(web({url: fixture("rss/atom.xml")}).http, url)).items

    assert item.title == "Releasing a 7B open-weight model"
    assert item.lead == "Weights, data mix and training settings are public."


def test_feed_discovery_finds_rss_and_atom_links_as_absolute_urls(fixture: Fixture) -> None:
    html = fixture("rss/homepage.html").decode()

    assert discover_feeds(html, "https://lab.example.org/") == [
        "https://lab.example.org/blog/feed.xml",
        "https://lab.example.org/atom.xml",
    ]


async def test_arxiv_items_link_to_the_abstract_without_a_version(
    fixture: Fixture, web: Web
) -> None:
    recorded = web({"https://export.arxiv.org/api/query": fixture("arxiv/query.xml")})

    outcome = await fetch_arxiv(recorded.http, 'abs:"open-weight"')

    assert len(outcome.items) == 3
    first = outcome.items[0]
    assert first.url == "https://arxiv.org/abs/2610.13895"
    assert first.title == "Task Context Shapes Component Roles in Language Models"
    assert first.lead.startswith("Large language models reuse the same attention heads")
    query = parse_qs(urlsplit(str(recorded.requests[0].url)).query)
    assert query["search_query"] == ['abs:"open-weight"']
    assert query["sortBy"] == ["submittedDate"]


async def test_github_releases_skip_prereleases(fixture: Fixture, web: Web) -> None:
    recorded = web({"https://api.github.com/repos/": fixture("github/releases.json")})

    outcome = await fetch_github_releases(recorded.http, "vllm-project/vllm")

    assert [item.title for item in outcome.items] == [
        "vllm-project/vllm v0.31.0",
        "vllm-project/vllm v0.30.0",
        "vllm-project/vllm v0.29.0",
    ]
    assert outcome.items[0].url == "https://github.com/vllm-project/vllm/releases/tag/v0.31.0"
    assert "Authorization" not in recorded.requests[0].headers


async def test_a_github_token_is_sent_when_configured(fixture: Fixture, web: Web) -> None:
    recorded = web({"https://api.github.com/repos/": fixture("github/releases.json")})

    await fetch_github_releases(recorded.http, "vllm-project/vllm", token="t0ken")

    assert recorded.requests[0].headers["Authorization"] == "Bearer t0ken"


async def test_hacker_news_filters_by_points_and_window(fixture: Fixture, web: Web) -> None:
    recorded = web({"https://hn.algolia.com/": fixture("hackernews/search.json")})

    outcome = await fetch_hackernews(recorded.http, "open weights", min_points=50, since=NOW)

    assert len(outcome.items) == 4
    assert outcome.items[0].url == "https://reflection.ai/blog/introducing-beam"
    assert outcome.items[-1].url == "https://news.ycombinator.com/item?id=49950000"
    query = parse_qs(urlsplit(str(recorded.requests[0].url)).query)
    assert query["numericFilters"] == [f"points>=50,created_at_i>{int(NOW.timestamp())}"]
    assert query["typoTolerance"] == ["false"]


async def test_fetch_source_dispatches_on_the_source_type(fixture: Fixture, web: Web) -> None:
    recorded = web({"https://hn.algolia.com/": fixture("hackernews/search.json")})
    source = SourceSpec(type="hackernews", locator="open weights", config={"min_points": 100})

    await fetch_source(recorded.http, source, now=NOW)

    query = parse_qs(urlsplit(str(recorded.requests[0].url)).query)
    assert query["numericFilters"][0].startswith("points>=100,")
