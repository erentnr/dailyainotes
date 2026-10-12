import pytest

from dailyainotes.domain.rank_fusion import reciprocal_rank_fusion


def test_an_item_both_methods_rank_well_beats_one_only_one_ranks_first() -> None:
    fused = reciprocal_rank_fusion({"full_text": [1, 2, 3], "vector": [2, 4, 1]})

    assert [f.id for f in fused][:2] == [2, 1]


def test_each_item_keeps_its_rank_in_every_method_that_found_it() -> None:
    fused = {f.id: f for f in reciprocal_rank_fusion({"full_text": [7], "vector": [8, 7]})}

    assert fused[7].ranks == {"full_text": 1, "vector": 2}
    assert fused[8].ranks == {"vector": 1}


def test_the_score_is_the_sum_of_one_over_k_plus_rank() -> None:
    (only,) = reciprocal_rank_fusion({"a": [5], "b": [5]}, k=60)

    assert only.score == pytest.approx(2 / 61)


def test_ties_are_broken_by_id_so_the_order_is_stable() -> None:
    fused = reciprocal_rank_fusion({"a": [9, 3], "b": [3, 9]})

    assert [f.id for f in fused] == [3, 9]


def test_no_rankings_means_no_results() -> None:
    assert reciprocal_rank_fusion({"a": [], "b": []}) == []
