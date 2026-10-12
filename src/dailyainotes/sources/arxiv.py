"""arXiv API search. Metadata, abstracts included, is CC0; we link to the abstract page and
never host PDFs. Requests to arXiv are spaced 3 seconds apart (sources/http.py)."""

import re
from urllib.parse import urlencode

import feedparser

from dailyainotes.sources.http import Http
from dailyainotes.sources.items import LEAD_LIMIT, FetchOutcome, RawItem, from_struct_time

ARXIV_API = "https://export.arxiv.org/api/query"
VERSION_SUFFIX = re.compile(r"v\d+$")


async def fetch_arxiv(http: Http, query: str, *, max_results: int = 50) -> FetchOutcome:
    parameters = {
        "search_query": query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": max_results,
    }
    response = await http.get(f"{ARXIV_API}?{urlencode(parameters)}")
    response.raise_for_status()
    feed = feedparser.parse(response.content)
    return FetchOutcome(
        [
            RawItem(
                url=abstract_url(entry.id),
                title=" ".join(entry.title.split()),
                lead=" ".join(entry.summary.split())[:LEAD_LIMIT],
                published_at=from_struct_time(entry.get("published_parsed")),
            )
            for entry in feed.entries
        ]
    )


def abstract_url(entry_id: str) -> str:
    """`http://arxiv.org/abs/2610.13895v1` → `https://arxiv.org/abs/2610.13895`, one URL for
    every version of a paper."""
    paper = VERSION_SUFFIX.sub("", entry_id.rsplit("/abs/", 1)[-1])
    return f"https://arxiv.org/abs/{paper}"
