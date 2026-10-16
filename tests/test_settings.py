import pytest
from pydantic import ValidationError

from dailyainotes.settings import Settings


def test_log_level_defaults_to_info(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    assert Settings(_env_file=None).log_level == "INFO"


def test_log_level_comes_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    assert Settings(_env_file=None).log_level == "DEBUG"


def test_an_unknown_log_level_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "LOUD")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_swapped_langfuse_keys_are_named_without_showing_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "sk-lf-secret-value")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "pk-lf-public-value")

    with pytest.raises(ValidationError, match="look swapped") as failure:
        Settings(_env_file=None)

    assert "secret-value" not in str(failure.value)
    assert "public-value" not in str(failure.value)


def test_langfuse_keys_in_their_right_places_are_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-1")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-2")

    assert Settings(_env_file=None).langfuse_public_key == "pk-lf-1"


def test_the_database_password_and_github_token_stay_out_of_the_repr() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://dan:not-a-real-password@db:5432/dailyainotes",
        github_token="ghp_not_a_real_token",
    )

    assert "not-a-real-password" not in repr(settings)
    assert "ghp_not_a_real_token" not in repr(settings)
