import pytest

from dailyainotes.domain.accounts import (
    code_digest,
    digest,
    is_valid_email,
    new_code,
    new_token,
    normalize_email,
)


@pytest.mark.parametrize(
    "email", ["reader@example.com", "first.last+news@mail.example.co.uk", "a@b.io"]
)
def test_ordinary_addresses_are_valid(email: str) -> None:
    assert is_valid_email(email)


@pytest.mark.parametrize(
    "email",
    [
        "",
        "reader",
        "reader@",
        "@example.com",
        "reader@example",
        "two words@example.com",
        "a@b@example.com",
        "reader@example.",
        f"{'a' * 250}@example.com",
    ],
)
def test_anything_else_is_not(email: str) -> None:
    assert not is_valid_email(email)


def test_an_address_is_compared_without_case_or_spaces() -> None:
    assert normalize_email("  Reader@Example.COM ") == "reader@example.com"


def test_a_code_is_six_digits_and_tokens_do_not_repeat() -> None:
    codes = {new_code() for _ in range(200)}

    assert all(len(c) == 6 and c.isdigit() for c in codes)
    assert len({new_token() for _ in range(200)}) == 200


def test_the_same_code_for_two_readers_is_stored_differently() -> None:
    assert code_digest("a@example.com", "123456") != code_digest("b@example.com", "123456")
    assert len(digest("token")) == 64
