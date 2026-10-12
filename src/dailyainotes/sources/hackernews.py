"""Hacker News stories through Algolia's search API (10,000 requests an hour per IP)."""

from datetime import datetime
from urllib.parse import urlencode

from dailyainotes.sources.http import Http
from dailyainotes.sources.items import FetchOutcome, RawItem, from_iso

ALGOLIA = "https://hn.algolia.com/api/v1/search_by_date"


async def fetch_hackernews(
    http: Http, query: str, *, min_points: int, since: datetime
) -> FetchOutcome:
    parameters = {
        "query": query,
        "tags": "story",
        "numericFilters": f"points>={min_points},created_at_i>{int(since.timestamp())}",
        # Without this, "rust" also matches "Russian".
        "typoTolerance": "false",
        "hitsPerPage": 50,
    }
    response = await http.get(f"{ALGOLIA}?{urlencode(parameters)}")
    response.raise_for_status()
    return FetchOutcome(
        [
            RawItem(
                # "Ask HN" posts have no URL; the discussion is the item.
                url=hit["url"] or f"https://news.ycombinator.com/item?id={hit['objectID']}",
                title=hit["title"],
                lead="",
                published_at=from_iso(hit["created_at"]),
            )
            for hit in response.json()["hits"]
        ]
    )
