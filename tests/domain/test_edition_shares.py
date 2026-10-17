from datetime import date

from dailyainotes.domain.editorial import story_shares

TOPICS = [f"topic-{n:02d}" for n in range(12)]
DAY = date(2026, 10, 17)


def test_every_topic_gets_a_story_before_any_gets_a_second() -> None:
    shares = story_shares(TOPICS, DAY, per_day=15, per_topic=2)

    assert sum(shares.values()) == 15
    assert sorted(shares.values()) == [1] * 9 + [2] * 3


def test_the_second_stories_move_to_other_topics_the_next_day() -> None:
    today = story_shares(TOPICS, DAY, per_day=15, per_topic=2)
    tomorrow = story_shares(TOPICS, date(2026, 10, 18), per_day=15, per_topic=2)

    twice_today = {t for t, n in today.items() if n == 2}
    twice_tomorrow = {t for t, n in tomorrow.items() if n == 2}
    assert twice_today.isdisjoint(twice_tomorrow)


def test_few_topics_each_get_the_most_a_topic_may_have() -> None:
    assert story_shares(TOPICS[:5], DAY, per_day=15, per_topic=2) == dict.fromkeys(TOPICS[:5], 2)


def test_more_topics_than_the_day_allows_take_turns_with_one_story() -> None:
    many = [f"topic-{n:02d}" for n in range(20)]

    shares = story_shares(many, DAY, per_day=15, per_topic=2)
    tomorrow = story_shares(many, date(2026, 10, 18), per_day=15, per_topic=2)

    assert sorted(shares.values()) == [0] * 5 + [1] * 15
    assert {t for t, n in shares.items() if n == 0} != {t for t, n in tomorrow.items() if n == 0}
