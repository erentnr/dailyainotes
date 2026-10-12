from collections.abc import Callable
from typing import Any

import pytest

from dailyainotes.sources.fetcher import ArticleFetcher

pytestmark = pytest.mark.anyio

Fixture = Callable[[str], bytes]
Web = Callable[[dict[str, Any]], Any]
SITE = "https://news.example.com"
PAGE = f"{SITE}/2026/10/12/storage-pilot"
ROBOTS = f"{SITE}/robots.txt"
HTML = {"Content-Type": "text/html; charset=utf-8"}


def fetcher(web: Web, page: Any, robots: Any = (404, b"", {})) -> tuple[ArticleFetcher, Any]:
    recorded = web({ROBOTS: robots, PAGE: page})
    return ArticleFetcher(recorded.http), recorded


async def test_an_open_article_is_extracted_in_full(fixture: Fixture, web: Web) -> None:
    gate, _ = fetcher(web, (200, fixture("pages/article.html"), HTML))

    decision = await gate.decide(PAGE)

    assert decision.text_policy == "full"
    assert decision.content is not None
    assert "The pilot project began operating this week" in decision.content
    assert "Home" not in decision.content


@pytest.mark.parametrize(
    ("page", "reason"),
    [
        ("pages/meta-noai.html", "meta robots: noai"),
        ("pages/meta-nosnippet.html", "meta robots: nosnippet"),
        ("pages/meta-tdm.html", "meta tdm-reservation: 1"),
        ("pages/paywall-jsonld.html", "paywalled (isAccessibleForFree: false)"),
    ],
)
async def test_a_page_that_opts_out_is_link_only(
    fixture: Fixture, web: Web, page: str, reason: str
) -> None:
    gate, _ = fetcher(web, (200, fixture(page), HTML))

    decision = await gate.decide(PAGE)

    assert (decision.text_policy, decision.reason, decision.content) == ("link_only", reason, None)


@pytest.mark.parametrize(
    ("header", "reason"),
    [
        ({"X-Robots-Tag": "noai, noimageai"}, "X-Robots-Tag: noai"),
        ({"Content-Usage": "ai-use=n"}, "Content-Usage: ai-use=n"),
        ({"tdm-reservation": "1"}, "tdm-reservation: 1"),
    ],
)
async def test_a_response_header_that_opts_out_is_link_only(
    fixture: Fixture, web: Web, header: dict[str, str], reason: str
) -> None:
    gate, _ = fetcher(web, (200, fixture("pages/article.html"), HTML | header))

    decision = await gate.decide(PAGE)

    assert (decision.text_policy, decision.reason) == ("link_only", reason)


@pytest.mark.parametrize(
    ("robots", "reason"),
    [
        ("User-agent: DailyAINotes\nDisallow: /\n", "robots.txt disallows us"),
        (
            "User-agent: *\nContent-Signal: search=yes, ai-input=no\nAllow: /\n",
            "Content-Signal: ai-input=no",
        ),
        (
            "User-agent: *\nContent-Signal: search=yes, ai-train=no, use=reference\n",
            "Content-Signal: use=reference",
        ),
        ("User-agent: *\nContent-Usage: ai-use=n\n", "robots.txt Content-Usage: ai-use=n"),
        (
            "User-agent: GPTBot\nDisallow: /\n\n"
            "User-agent: ClaudeBot\nUser-agent: CCBot\nDisallow: /\n",
            "robots.txt blocks AI crawlers (ccbot, claudebot, gptbot)",
        ),
    ],
)
async def test_robots_txt_rules_and_ai_opt_outs_make_a_page_link_only(
    fixture: Fixture, web: Web, robots: str, reason: str
) -> None:
    gate, recorded = fetcher(web, (200, fixture("pages/article.html"), HTML), robots.encode())

    decision = await gate.decide(PAGE)

    assert (decision.text_policy, decision.reason) == ("link_only", reason)
    assert [str(r.url) for r in recorded.requests] == [ROBOTS]


async def test_one_blocked_ai_crawler_alone_is_not_an_opt_out(fixture: Fixture, web: Web) -> None:
    robots = b"User-agent: GPTBot\nDisallow: /\n\nUser-agent: *\nAllow: /\n"
    gate, _ = fetcher(web, (200, fixture("pages/article.html"), HTML), robots)

    assert (await gate.decide(PAGE)).text_policy == "full"


async def test_an_unreachable_robots_txt_means_disallow_everything(
    fixture: Fixture, web: Web
) -> None:
    gate, _ = fetcher(web, (200, fixture("pages/article.html"), HTML), (503, b"", {}))

    decision = await gate.decide(PAGE)

    assert (decision.text_policy, decision.reason) == ("link_only", "robots.txt returned 503")


async def test_robots_txt_is_fetched_once_per_site(fixture: Fixture, web: Web) -> None:
    gate, recorded = fetcher(web, (200, fixture("pages/article.html"), HTML))

    await gate.decide(PAGE)
    await gate.decide(PAGE)

    assert [str(r.url) for r in recorded.requests].count(ROBOTS) == 1


async def test_a_paywalled_publisher_is_never_fetched(web: Web) -> None:
    gate, recorded = fetcher(web, (200, b"", HTML))

    decision = await gate.decide(PAGE, publisher_paywalled=True)

    assert decision.text_policy == "link_only"
    assert recorded.requests == []


@pytest.mark.parametrize(
    "url",
    [
        "https://www.theguardian.com/science/2026/oct/12/comet",
        "https://www.nytimes.com/2026/10/12/science/comet.html",
        "https://old.reddit.com/r/space/comments/abc/comet/",
    ],
)
async def test_an_excluded_publisher_is_link_only_and_never_fetched(web: Web, url: str) -> None:
    recorded = web({})

    decision = await ArticleFetcher(recorded.http).decide(url)

    assert (decision.text_policy, decision.reason) == ("link_only", "excluded publisher")
    assert recorded.requests == []


async def test_a_forbidden_page_is_link_only(web: Web) -> None:
    gate, _ = fetcher(web, (403, b"", HTML))

    assert (await gate.decide(PAGE)).text_policy == "link_only"


async def test_a_teaser_page_falls_back_to_the_feed_summary(fixture: Fixture, web: Web) -> None:
    gate, _ = fetcher(web, (200, fixture("pages/thin.html"), HTML))

    decision = await gate.decide(PAGE)

    assert (decision.text_policy, decision.reason) == ("summary", "too little article text")
