"""Publisher signals that decide what we may do with a page (INTENT.md, Copyright).

Pure parsing, no I/O: robots.txt rules and AI opt-outs, response headers, and the page's
own meta tags and JSON-LD. sources/fetcher.py applies them in order.
"""

import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any
from urllib.robotparser import RobotFileParser

# The product token we match in robots.txt (RFC 9309).
ROBOTS_PRODUCT = "DailyAINotes"
# Crawlers that only AI products use. A site that blocks two or more of them has said
# "no AI" in the only machine-readable way most sites have.
AI_CRAWLERS = {
    "gptbot",
    "chatgpt-user",
    "claudebot",
    "anthropic-ai",
    "ccbot",
    "google-extended",
    "perplexitybot",
    "bytespider",
    "applebot-extended",
    "meta-externalagent",
}
AI_CRAWLER_THRESHOLD = 2
OPT_OUT_ROBOTS_DIRECTIVES = {"noai", "nosnippet"}


@dataclass(frozen=True)
class RobotsPolicy:
    """What a site's robots.txt says about us. `opt_out` is a reason, or empty."""

    parser: RobotFileParser
    opt_out: str

    def allows(self, url: str) -> bool:
        return self.parser.can_fetch(ROBOTS_PRODUCT, url)


def allow_all() -> RobotsPolicy:
    return RobotsPolicy(rules(["User-agent: *", "Allow: /"]), "")


def deny_all(reason: str) -> RobotsPolicy:
    return RobotsPolicy(rules(["User-agent: *", "Disallow: /"]), reason)


def parse_robots(text: str) -> RobotsPolicy:
    lines = text.splitlines()
    return RobotsPolicy(rules(lines), robots_opt_out(lines))


def rules(lines: list[str]) -> RobotFileParser:
    parser = RobotFileParser()
    parser.parse(lines)
    # can_fetch() refuses everything until the parser has been marked as read.
    parser.modified()
    return parser


def robots_opt_out(lines: list[str]) -> str:
    blocked: set[str] = set()
    agents: list[str] = []
    in_rules = False
    for raw in lines:
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        field, value = (part.strip() for part in line.split(":", 1))
        field = field.lower()
        if field == "user-agent":
            if in_rules:
                agents, in_rules = [], False
            agents.append(value.lower())
        elif field in ("allow", "disallow"):
            in_rules = True
            if field == "disallow" and value == "/":
                blocked.update(agent for agent in agents if agent in AI_CRAWLERS)
        elif field == "content-signal" and (reason := content_signal_opt_out(value)):
            return reason
        elif field == "content-usage" and "ai-use=n" in value.replace(" ", "").lower():
            return "robots.txt Content-Usage: ai-use=n"
    if len(blocked) >= AI_CRAWLER_THRESHOLD:
        return f"robots.txt blocks AI crawlers ({', '.join(sorted(blocked))})"
    return ""


def content_signal_opt_out(value: str) -> str:
    """Cloudflare Content Signals. Summarizing is AI input, and `use=` short of `full` rules
    out summaries."""
    signals = dict(
        (pair.split("=", 1)[0].strip().lower(), pair.split("=", 1)[1].strip().lower())
        for pair in value.split(",")
        if "=" in pair
    )
    if signals.get("ai-input") == "no":
        return "Content-Signal: ai-input=no"
    if signals.get("use") in ("reference", "immediate"):
        return f"Content-Signal: use={signals['use']}"
    return ""


def header_opt_out(headers: dict[str, str]) -> str:
    lowered = {key.lower(): value.lower() for key, value in headers.items()}
    directives = set(re.split(r"[\s,]+", lowered.get("x-robots-tag", "")))
    if found := directives & OPT_OUT_ROBOTS_DIRECTIVES:
        return f"X-Robots-Tag: {', '.join(sorted(found))}"
    if "ai-use=n" in lowered.get("content-usage", "").replace(" ", ""):
        return "Content-Usage: ai-use=n"
    if lowered.get("tdm-reservation", "").strip() == "1":
        return "tdm-reservation: 1"
    return ""


class _HeadParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta: dict[str, str] = {}
        self.json_ld: list[str] = []
        self._in_json_ld = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        if tag == "meta" and "name" in values:
            self.meta[values["name"].lower()] = values.get("content", "").lower()
        self._in_json_ld = tag == "script" and values.get("type") == "application/ld+json"

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self._in_json_ld = False

    def handle_data(self, data: str) -> None:
        if self._in_json_ld:
            self.json_ld.append(data)


def page_opt_out(html: str) -> str:
    parser = _HeadParser()
    parser.feed(html)
    directives = set(re.split(r"[\s,]+", parser.meta.get("robots", "")))
    if found := directives & OPT_OUT_ROBOTS_DIRECTIVES:
        return f"meta robots: {', '.join(sorted(found))}"
    if parser.meta.get("tdm-reservation") == "1":
        return "meta tdm-reservation: 1"
    for block in parser.json_ld:
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        if any(value in (False, "false", "False") for value in accessible_for_free(data)):
            return "paywalled (isAccessibleForFree: false)"
    return ""


def accessible_for_free(data: Any) -> Iterator[Any]:
    """Every `isAccessibleForFree` value in a JSON-LD document, at any depth."""
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "isAccessibleForFree":
                yield value
            else:
                yield from accessible_for_free(value)
    elif isinstance(data, list):
        for item in data:
            yield from accessible_for_free(item)
