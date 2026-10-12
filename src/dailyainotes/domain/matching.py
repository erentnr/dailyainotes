"""How well a source's items match a topic: the share of items that name one of its terms."""

import re


def match_share(texts: list[str], terms: list[str]) -> float:
    """Share of `texts` containing any term as whole words, ignoring case; 0 for no texts."""
    if not texts or not terms:
        return 0.0
    pattern = re.compile(
        r"\b(?:" + "|".join(re.escape(term) for term in terms) + r")\b", re.IGNORECASE
    )
    return sum(1 for text in texts if pattern.search(text)) / len(texts)
