"""How well a source's items match a topic: the share of items that name one of its terms, or
whose closest topic is this one."""

import math
import re


def match_share(texts: list[str], terms: list[str]) -> float:
    """Share of `texts` containing any term as whole words, ignoring case; 0 for no texts."""
    if not texts or not terms:
        return 0.0
    pattern = re.compile(
        r"\b(?:" + "|".join(re.escape(term) for term in terms) + r")\b", re.IGNORECASE
    )
    return sum(1 for text in texts if pattern.search(text)) / len(texts)


def nearest_share(items: list[list[float]], topics: list[list[float]], target: int) -> float:
    """Share of item vectors strictly closer to `topics[target]` than to every other topic; 0
    for no items. Comparing against every topic, not one threshold, copes with topics whose
    names are more or less specific (calibrated 2026-10-16, MEMORY.md)."""
    if not items:
        return 0.0
    closer = 0
    for item in items:
        sims = [cosine(item, topic) for topic in topics]
        others = sims[:target] + sims[target + 1 :]
        closer += all(sims[target] > other for other in others)
    return closer / len(items)


def cosine(a: list[float], b: list[float]) -> float:
    norms = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return sum(x * y for x, y in zip(a, b, strict=True)) / norms if norms else 0.0
