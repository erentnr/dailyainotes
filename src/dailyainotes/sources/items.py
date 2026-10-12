"""What every connector returns, and the small text helpers they share."""

import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser

# The longest lead we keep: enough to match a story, short of republishing it.
LEAD_LIMIT = 1000

# WordPress feeds end every description with "The post X appeared first on Y."
WORDPRESS_FOOTER = re.compile(r"\s*The post .* appeared first on .*$", re.DOTALL)


@dataclass(frozen=True)
class RawItem:
    url: str
    title: str
    # The publisher's own description, abstract or release notes, as plain text.
    lead: str
    published_at: datetime | None


@dataclass(frozen=True)
class FetchOutcome:
    items: list[RawItem]
    etag: str | None = None
    last_modified: str | None = None
    not_modified: bool = False


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def html_to_text(markup: str) -> str:
    parser = _TextParser()
    parser.feed(markup)
    parser.close()
    return " ".join(" ".join(parser.parts).split())


def clean_lead(markup: str) -> str:
    return WORDPRESS_FOOTER.sub("", html_to_text(markup))[:LEAD_LIMIT]


def from_struct_time(value: time.struct_time | None) -> datetime | None:
    """feedparser gives UTC `struct_time`s."""
    if value is None:
        return None
    return datetime(*value[:6], tzinfo=UTC)


def from_iso(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None
