import json
import logging
from typing import Any

import pytest
import structlog

from dailyainotes.logging import configure_logging


def last_line(capsys: pytest.CaptureFixture[str]) -> dict[str, Any]:
    lines = capsys.readouterr().out.strip().splitlines()
    parsed: dict[str, Any] = json.loads(lines[-1])
    return parsed


def test_our_events_are_json_lines_with_level_and_utc_time(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging("INFO")

    structlog.get_logger("dailyainotes.test").info("source_fetched", source="arxiv", items=3)

    line = last_line(capsys)
    assert line["event"] == "source_fetched"
    assert line["level"] == "info"
    assert line["source"] == "arxiv"
    assert line["items"] == 3
    assert line["timestamp"].endswith("Z")


def test_library_logs_have_the_same_json_shape(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO")

    logging.getLogger("uvicorn.error").warning("port in use")

    line = last_line(capsys)
    assert line["event"] == "port in use"
    assert line["level"] == "warning"
    assert line["logger"] == "uvicorn.error"


def test_events_below_the_configured_level_are_dropped(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging("WARNING")

    structlog.get_logger("dailyainotes.test").info("source_fetched")

    assert capsys.readouterr().out == ""
