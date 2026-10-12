import pytest

from dailyainotes.domain.answers import AnswerFilter


def stream(chunks: list[str], sources: int = 2) -> tuple[str, AnswerFilter]:
    answer = AnswerFilter(sources)
    shown = "".join(answer.feed(chunk) for chunk in chunks) + answer.flush()
    return shown, answer


def test_valid_markers_pass_and_are_recorded_once_in_order() -> None:
    shown, answer = stream(["The race was wet [2]. ", "The safety car came out [1][2]."])

    assert shown == "The race was wet [2]. The safety car came out [1][2]."
    assert answer.cited == [2, 1]


@pytest.mark.parametrize(
    "chunks",
    [
        ["The race was wet [3]."],
        ["The race was wet [", "3]."],
        ["The race was wet ", "[", "3", "]", "."],
    ],
)
def test_a_marker_that_points_nowhere_is_dropped_even_split_across_chunks(
    chunks: list[str],
) -> None:
    shown, answer = stream(chunks)

    assert shown == "The race was wet."
    assert answer.cited == []


def test_a_split_valid_marker_is_held_back_until_complete() -> None:
    answer = AnswerFilter(2)

    assert answer.feed("It rained [") == "It rained"
    assert answer.feed("1") == ""
    assert answer.feed("]. Then") == " [1]. Then"


@pytest.mark.parametrize(
    "chunks", [["NOT_ENOUGH"], ["NOT_", "ENOUGH"], ["  NOT", "_ENOUGH\n", "sorry [1]"]]
)
def test_not_enough_shows_nothing_and_is_flagged(chunks: list[str]) -> None:
    shown, answer = stream(chunks)

    assert shown == ""
    assert answer.insufficient


def test_an_answer_that_starts_like_not_enough_but_is_not_is_shown() -> None:
    shown, answer = stream(["NOT", " every team agreed [1]."])

    assert shown == "NOT every team agreed [1]."
    assert not answer.insufficient


def test_a_truncated_not_enough_is_still_not_enough() -> None:
    shown, answer = stream(["NOT_ENO"])

    assert (shown, answer.insufficient) == ("", True)
