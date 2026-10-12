"""Group documents about the same event into stories.

One pass in publication order: a document joins the story whose centroid it is closest to,
if that similarity reaches the threshold, and starts a new story otherwise. Splitting one
event in two is the safer error: a duplicate note costs a review, a note that mixes two
events misleads.
"""

import math
from dataclasses import dataclass
from datetime import datetime

# Calibrated on 112 Formula 1 documents from one race weekend (MEMORY.md, 2026-10-13):
# reports of the same event scored 0.92 to 0.99, different events of that weekend up to 0.92.
SAME_STORY = 0.92


@dataclass(frozen=True)
class Item:
    id: int
    # A unit vector (the local model normalizes its embeddings).
    vector: list[float]
    published_at: datetime | None


@dataclass
class Cluster:
    ids: list[int]
    # The sum of its members' vectors; its direction is the centroid's.
    total: list[float]

    def similarity(self, vector: list[float]) -> float:
        """Cosine similarity between the centroid and a unit vector."""
        norm = math.sqrt(sum(x * x for x in self.total))
        return sum(a * b for a, b in zip(self.total, vector, strict=True)) / norm


def cluster(items: list[Item], *, threshold: float = SAME_STORY) -> list[list[int]]:
    """Document ids grouped by story, each group in publication order."""
    clusters: list[Cluster] = []
    undated_last = sorted(items, key=lambda i: (i.published_at is None, i.published_at or 0))
    for item in undated_last:
        scored = [(c.similarity(item.vector), c) for c in clusters]
        similarity, best = max(scored, key=lambda s: s[0], default=(0.0, None))
        if best and similarity >= threshold:
            best.ids.append(item.id)
            best.total = [a + b for a, b in zip(best.total, item.vector, strict=True)]
        else:
            clusters.append(Cluster([item.id], list(item.vector)))
    return [c.ids for c in clusters]
