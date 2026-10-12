from dailyainotes.evals import QuestionResult, regressions, score


def test_scores_count_hits_ranks_and_not_enough() -> None:
    results = [
        QuestionResult(1, "q1", "a", sources=["a", "b"]),
        QuestionResult(2, "q2", "c", sources=["d", "c"]),
        QuestionResult(3, "q3", "e", sources=["f"]),
        QuestionResult(4, "q4", None, sources=[]),
        QuestionResult(5, "q5", None, sources=["a"]),
    ]

    assert score(results) == {
        "questions": 5,
        "recall_at_5": 0.667,
        "mrr": 0.5,
        "not_enough_when_uncovered": 0.5,
    }


def test_faithfulness_is_scored_only_over_judged_answers() -> None:
    results = [
        QuestionResult(1, "q1", "a", ["a"], answer="x [1].", faithful=True),
        QuestionResult(2, "q2", "b", ["b"], answer="y [1].", faithful=False),
        QuestionResult(3, "q3", None, []),
    ]

    assert score(results)["faithfulness"] == 0.5


def test_a_score_below_its_baseline_is_a_regression() -> None:
    baseline = {"recall_at_5": 1.0, "mrr": 0.9}

    assert regressions({"recall_at_5": 1.0, "mrr": 0.95}, baseline) == []
    assert regressions({"recall_at_5": 0.95, "mrr": 0.9}, baseline) == [
        "recall_at_5 fell from 1.0 to 0.95"
    ]
