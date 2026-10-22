from datetime import UTC, date, datetime, timedelta

import pytest

from dailyainotes.domain.editorial import (
    Report,
    check_citations,
    cross_owner_disagreements,
    final_verdict,
    first_words,
    next_step,
    rank_story,
    slugify,
    sole_publisher,
)

NOW = datetime(2026, 10, 13, 12, tzinfo=UTC)
EVIDENCE = {
    1: "The utility said the 10 MW system can discharge for up to 100 hours.",
    2: "One outlet put the pilot at 15 MW. It will run for two years.",
}


def report(group: str, trust: float, hours_ago: float = 1) -> Report:
    return Report(group, trust, NOW - timedelta(hours=hours_ago))


def test_independent_publishers_outrank_many_copies_from_one_group() -> None:
    independent = rank_story([report("a", 0.75), report("b", 0.75)], NOW)
    one_group = rank_story([report("a", 0.75), report("a", 0.75), report("a", 0.75)], NOW)

    assert independent.score > one_group.score
    assert independent.independent == 2
    assert one_group.reasons[0] == "3 reports from 1 independent publishers"


def test_fresher_coverage_ranks_higher() -> None:
    assert (
        rank_story([report("a", 0.75, 1)], NOW).score
        > rank_story([report("a", 0.75, 30)], NOW).score
    )


def test_a_cited_sentence_with_numbers_from_its_evidence_passes() -> None:
    text = "A 10 MW pilot can discharge for 100 hours [1]. It runs for two years [2]."

    assert check_citations(text, EVIDENCE) == []


@pytest.mark.parametrize(
    ("text", "problem"),
    [
        ("The pilot is large.", "No citation"),
        ("The pilot is large [3].", "does not exist [3]"),
        ("The pilot stores 400 MWh [1].", "The number 400 is not in the cited evidence"),
        ("The pilot is 15 MW [1].", "The number 15 is not in the cited evidence"),
        ('The utility called it "a world first for storage" [1].', "not verbatim"),
    ],
)
def test_citation_problems_are_found_without_a_model(text: str, problem: str) -> None:
    (found,) = check_citations(text, EVIDENCE)

    assert problem in found


def test_a_number_written_with_a_thousands_comma_still_matches() -> None:
    assert check_citations("It cost 1,200 dollars [1].", {1: "It cost 1200 dollars."}) == []


def test_a_factual_claim_needs_two_independent_origins_one_trusted() -> None:
    assert final_verdict("supported", "factual", [report("a", 0.75)]) == ("weak", 1)
    assert final_verdict("supported", "factual", [report("a", 0.75), report("a", 0.6)]) == (
        "weak",
        1,
    )
    assert final_verdict("supported", "factual", [report("a", 0.75), report("b", 0.5)]) == (
        "supported",
        2,
    )
    assert final_verdict("supported", "factual", [report("a", 0.6), report("b", 0.6)]) == (
        "weak",
        2,
    )


def test_a_primary_source_alone_supports_a_claim_about_itself() -> None:
    assert final_verdict("supported", "numeric", [report("fia", 0.85)]) == ("supported", 1)


def test_an_attributed_claim_needs_only_its_source() -> None:
    assert final_verdict("supported", "attributed", [report("a", 0.35)]) == ("supported", 1)


def test_the_model_saying_unsupported_is_kept() -> None:
    assert final_verdict("unsupported", "factual", []) == ("unsupported", 0)


def test_a_clean_draft_goes_to_review_and_a_flawed_one_is_rewritten_twice_at_most() -> None:
    assert next_step([], ["supported", "supported"], rewrites=0) == "publish"
    assert next_step(["No citation"], ["supported"], rewrites=0) == "write"
    assert next_step([], ["supported", "weak"], rewrites=1) == "write"
    assert next_step([], ["weak"], rewrites=2) == "publish"


def test_a_slug_is_the_date_and_the_title_in_ascii() -> None:
    assert slugify("Verstappen\u2019s Grand Prix: wins again!", date(2026, 10, 13)) == (
        "2026-10-13-verstappens-grand-prix-wins-again"
    )


def test_a_quote_is_at_most_twenty_five_words() -> None:
    assert first_words(" ".join(["word"] * 30)).split()[-1] == "word…"
    assert len(first_words(" ".join(["word"] * 30)).split()) == 25
    assert first_words("short quote") == "short quote"


def test_evidence_from_one_owner_group_names_its_publisher() -> None:
    assert sole_publisher([("The Race", "the-race.com", 0.6)]) == "The Race"
    assert (
        sole_publisher([("Autosport", "motorsport", 0.75), ("Motorsport.com", "motorsport", 0.75)])
        == "Autosport"
    )


def test_a_second_owner_group_or_a_primary_source_needs_no_attribution() -> None:
    assert (
        sole_publisher([("The Race", "the-race.com", 0.6), ("RaceFans", "racefans.net", 0.6)])
        is None
    )
    assert sole_publisher([("Formula 1", "formula1.com", 0.85)]) is None
    assert sole_publisher([]) is None


OWNED_EVIDENCE = {
    1: {
        "owner_group": "fia",
        "publisher": "Fia",
        "title": "Result",
        "url": "https://fia.example/1",
    },
    2: {
        "owner_group": "wire",
        "publisher": "Wire",
        "title": "Report",
        "url": "https://wire.example/2",
    },
    3: {
        "owner_group": "wire",
        "publisher": "Wire Sport",
        "title": "Copy",
        "url": "https://wire.example/3",
    },
}


def test_a_disagreement_between_publishers_with_different_owners_is_kept() -> None:
    brief = [
        {
            "point": "The winning margin",
            "positions": [
                {"says": "4.2 seconds", "evidence": [1]},
                {"says": "5.1 seconds", "evidence": [2]},
            ],
        }
    ]

    (kept,) = cross_owner_disagreements(brief, OWNED_EVIDENCE)

    assert kept["point"] == "The winning margin"
    assert [(p["says"], [s["publisher"] for s in p["sources"]]) for p in kept["positions"]] == [
        ("4.2 seconds", ["Fia"]),
        ("5.1 seconds", ["Wire"]),
    ]
    assert kept["positions"][1]["sources"][0]["url"] == "https://wire.example/2"


def test_positions_from_one_owner_or_unknown_evidence_are_no_disagreement() -> None:
    same_owner = {
        "point": "p",
        "positions": [{"says": "a", "evidence": [2]}, {"says": "b", "evidence": [3]}],
    }
    unknown = {
        "point": "q",
        "positions": [{"says": "a", "evidence": [1]}, {"says": "b", "evidence": [9]}],
    }
    one_side = {"point": "r", "positions": [{"says": "a", "evidence": [1, 2]}]}

    assert cross_owner_disagreements([same_owner, unknown, one_side], OWNED_EVIDENCE) == []
