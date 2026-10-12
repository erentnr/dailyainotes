"""Reciprocal rank fusion: merge rankings by summing 1 / (k + rank) for each item.

It needs no score calibration between methods, which is why it suits merging full-text and
vector search, whose scores are not comparable.
"""

from dataclasses import dataclass

RRF_K = 60


@dataclass(frozen=True)
class Fused:
    id: int
    score: float
    # Rank (1 is best) in each method that found the item.
    ranks: dict[str, int]


def reciprocal_rank_fusion(rankings: dict[str, list[int]], *, k: int = RRF_K) -> list[Fused]:
    """`rankings` maps a method's name to item ids, best first. Ties go to the lower id, so
    the order is the same on every run."""
    ranks: dict[int, dict[str, int]] = {}
    for method, ids in rankings.items():
        for rank, item in enumerate(ids, start=1):
            ranks.setdefault(item, {})[method] = rank
    fused = [
        Fused(item, sum(1 / (k + rank) for rank in by_method.values()), by_method)
        for item, by_method in ranks.items()
    ]
    return sorted(fused, key=lambda f: (-f.score, f.id))
