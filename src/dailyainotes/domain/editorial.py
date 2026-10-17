"""Editorial rules as plain functions: ranking stories, checking citations without a model,
judging claims by independent sources, and deciding where a draft goes next."""

import math
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

Verdict = Literal["supported", "weak", "unsupported", "contradicted"]
ClaimKind = Literal["factual", "numeric", "attributed", "context"]

MAX_REWRITES = 2
# A factual claim needs two independent origins, one at least this trusted, or one primary
# source (INTENT.md, Architectural Constraints).
TRUSTED = 0.7
PRIMARY = 0.85

MARKER = re.compile(r"\[(\d+)\]")
# A sentence ends at . ! or ? before a capital, a digit, a bracket or an opening quote.
SENTENCE_END = re.compile("(?<=[.!?])\\s+(?=[A-Z0-9\"\u201c\u2018'(])")
NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
QUOTED = re.compile(r"[\"“]([^\"”]+)[\"”]")


@dataclass(frozen=True)
class Report:
    """One document in a story, as ranking and fact-checking see it."""

    owner_group: str
    trust: float
    published_at: datetime | None


@dataclass(frozen=True)
class Ranked:
    score: float
    independent: int
    reasons: list[str]


def rank_story(reports: list[Report], now: datetime) -> Ranked:
    """Independent coverage counts most: the best trust in each owner group, summed. Size and
    freshness break ties."""
    best: dict[str, float] = {}
    for report in reports:
        best[report.owner_group] = max(best.get(report.owner_group, 0.0), report.trust)
    dated = [r.published_at for r in reports if r.published_at]
    hours = (now - max(dated)).total_seconds() / 3600 if dated else 24.0
    score = sum(best.values()) + 0.1 * math.log1p(len(reports)) + math.exp(-max(hours, 0) / 24)
    reasons = [
        f"{len(reports)} reports from {len(best)} independent publishers",
        f"latest {round(hours)} h ago" if dated else "undated",
    ]
    return Ranked(round(score, 3), len(best), reasons)


def sentences(text: str) -> list[str]:
    return [s for s in SENTENCE_END.split(text.strip()) if s]


def normalise_number(value: str) -> str:
    return value.replace(",", "")


def check_citations(text: str, evidence: dict[int, str]) -> list[str]:
    """Problems a model need not judge: a sentence without a marker, a marker that points
    nowhere, a number or a quote missing from the evidence the sentence cites."""
    problems: list[str] = []
    numbers_in = {n: {normalise_number(x) for x in NUMBER.findall(t)} for n, t in evidence.items()}
    for sentence in sentences(text):
        markers = [int(m) for m in MARKER.findall(sentence)]
        if not markers:
            problems.append(f"No citation: {sentence!r}")
            continue
        if missing := [m for m in markers if m not in evidence]:
            problems.append(f"Cites evidence that does not exist {missing}: {sentence!r}")
            continue
        cited = " ".join(evidence[m] for m in markers)
        for number in NUMBER.findall(MARKER.sub("", sentence)):
            if not any(normalise_number(number) in numbers_in[m] for m in markers):
                problems.append(f"The number {number} is not in the cited evidence: {sentence!r}")
        for quote in QUOTED.findall(sentence):
            if len(quote.split()) >= 3 and quote not in cited:
                problems.append(f"The quote is not verbatim in the cited evidence: {quote!r}")
    return problems


def final_verdict(
    model_verdict: Verdict, kind: ClaimKind, supporting: list[Report]
) -> tuple[Verdict, int]:
    """The verdict after the independence rule, and how many independent origins support it."""
    independent = len({r.owner_group for r in supporting})
    if model_verdict != "supported" or kind in ("attributed", "context"):
        return model_verdict, independent
    if any(r.trust >= PRIMARY for r in supporting):
        return "supported", independent
    trusted = any(r.trust >= TRUSTED for r in supporting)
    return ("supported" if independent >= 2 and trusted else "weak"), independent


def sole_publisher(evidence: list[tuple[str, str, float]]) -> str | None:
    """Given (publisher, owner group, trust) for each piece of evidence: the publisher, when
    all of it comes from one owner group and none is a primary source. Then no factual claim
    can find a second origin, so every fact must be attributed (INTENT.md, Fact-check rules)."""
    groups = {group for _, group, _ in evidence}
    if len(groups) != 1 or any(trust >= PRIMARY for _, _, trust in evidence):
        return None
    return evidence[0][0]


def next_step(problems: list[str], verdicts: list[Verdict], rewrites: int) -> str:
    """`write` for another attempt, `review` when the draft is clean or out of attempts."""
    clean = not problems and all(v == "supported" for v in verdicts)
    return "review" if clean or rewrites >= MAX_REWRITES else "write"


def without_markers(text: str) -> str:
    """A note's text for search and for Ask, where its own [n] markers mean nothing."""
    return re.sub(r"\s?\[\d+\]", "", text)


def search_text(title: str, body: str, why_it_matters: str) -> str:
    """What Ask searches and reads of a published note."""
    return "\n".join([title, without_markers(body), without_markers(why_it_matters)])


def slugify(title: str, day: date) -> str:
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    words = re.findall(r"[a-z0-9]+", ascii_title.lower())
    return f"{day.isoformat()}-{'-'.join(words)[:100].strip('-')}"


def first_words(text: str, limit: int = 25) -> str:
    """A quote of at most `limit` words (INTENT.md, Copyright)."""
    words = text.split()
    return " ".join(words[:limit]) + ("…" if len(words) > limit else "")


def story_shares(slugs: list[str], day: date, *, per_day: int, per_topic: int) -> dict[str, int]:
    """How many stories each topic may draft on a day: one each before any gets a second, up
    to `per_day` in all. The order goes round the topics and moves on each day by the slots
    one round leaves over, so the same topics do not always get the extra stories, or, when
    topics outnumber the day's stories, go without (found 2026-10-17: slug order left four
    topics with nothing)."""
    shares = dict.fromkeys(slugs, 0)
    if not slugs:
        return shares
    count = len(slugs)
    start = day.toordinal() * (per_day % count) % count
    order = slugs[start:] + slugs[:start]
    left = per_day
    for _ in range(per_topic):
        for slug in order:
            if left == 0:
                return shares
            shares[slug] += 1
            left -= 1
    return shares
