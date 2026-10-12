import math
from datetime import UTC, datetime, timedelta

from dailyainotes.domain.clustering import Item, cluster

NOON = datetime(2026, 10, 13, 12, tzinfo=UTC)


def unit(*values: float) -> list[float]:
    norm = math.sqrt(sum(v * v for v in values))
    return [v / norm for v in values]


def item(id_: int, vector: list[float], hours_ago: float | None = 1) -> Item:
    published = None if hours_ago is None else NOON - timedelta(hours=hours_ago)
    return Item(id_, vector, published)


def test_reports_of_one_event_form_one_story_and_others_stay_apart() -> None:
    items = [
        item(1, unit(1, 0.1, 0)),
        item(2, unit(1, 0.12, 0.02)),
        item(3, unit(0, 1, 0)),
        item(4, unit(0.98, 0.1, 0.05)),
    ]

    assert sorted(cluster(items)) == [[1, 2, 4], [3]]


def test_a_near_miss_starts_its_own_story() -> None:
    # cos(25°) ≈ 0.906, just below the threshold.
    angle = math.radians(25)

    assert cluster([item(1, unit(1, 0)), item(2, unit(math.cos(angle), math.sin(angle)))]) == [
        [1],
        [2],
    ]


def test_a_story_lists_its_reports_in_publication_order_with_undated_ones_last() -> None:
    items = [item(1, unit(1, 0), None), item(2, unit(1, 0), 1), item(3, unit(1, 0), 5)]

    assert cluster(items) == [[3, 2, 1]]
