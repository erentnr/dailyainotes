from dailyainotes.domain.matching import match_share, nearest_share

RACING, GARDENING = [1.0, 0.0], [0.0, 1.0]


def test_an_item_counts_for_the_topic_it_is_closest_to() -> None:
    items = [[0.9, 0.1], [0.8, 0.3], [0.2, 0.9], [0.1, 1.0]]

    assert nearest_share(items, [RACING, GARDENING], target=0) == 0.5
    assert nearest_share(items, [RACING, GARDENING], target=1) == 0.5


def test_an_item_as_close_to_another_topic_does_not_count() -> None:
    assert nearest_share([[0.5, 0.5], [0.0, 0.0]], [RACING, GARDENING], target=0) == 0.0


def test_no_items_share_nothing() -> None:
    assert nearest_share([], [RACING, GARDENING], target=0) == 0.0


def test_keywords_match_whole_words_ignoring_case() -> None:
    texts = ["A late Safety Car decides the race", "Safetycar is one word here"]

    assert match_share(texts, ["safety car"]) == 0.5
