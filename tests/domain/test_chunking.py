from dailyainotes.domain.chunking import chunk_text, heading_chunk


def test_short_paragraphs_are_packed_into_one_chunk() -> None:
    assert chunk_text("First paragraph.\n\nSecond   paragraph.\n") == [
        "First paragraph.\nSecond paragraph."
    ]


def test_paragraphs_start_a_new_chunk_when_the_limit_would_be_passed() -> None:
    text = "\n".join(["a" * 30, "b" * 30, "c" * 30])

    assert chunk_text(text, size=70) == ["a" * 30 + "\n" + "b" * 30, "c" * 30]


def test_a_long_paragraph_is_cut_at_word_boundaries() -> None:
    chunks = chunk_text("word " * 100, size=50)

    assert all(len(chunk) <= 50 for chunk in chunks)
    assert all(not chunk.startswith(" ") and not chunk.endswith(" ") for chunk in chunks)
    assert " ".join(chunks).split() == ["word"] * 100


def test_empty_text_has_no_chunks() -> None:
    assert chunk_text("  \n \n") == []


def test_the_heading_chunk_is_title_then_lead() -> None:
    assert heading_chunk("Title", "Lead text.") == "Title\nLead text."
    assert heading_chunk("Title", "") == "Title"
