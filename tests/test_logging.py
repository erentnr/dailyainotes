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


def test_uvicorn_access_lines_are_dropped_as_they_start_with_the_client_address(
    capsys: pytest.CaptureFixture[str],
) -> None:
    access = logging.getLogger("uvicorn.access")
    access.addHandler(logging.StreamHandler())
    access.propagate = False
    configure_logging("INFO")

    # The call uvicorn makes for each request.
    access.info('%s - "%s %s HTTP/%s" %d', "203.0.113.7:0", "POST", "/api/v1/ask", "1.1", 200)

    captured = capsys.readouterr()
    assert "203.0.113.7" not in captured.out + captured.err


def test_tracebacks_keep_the_error_but_not_the_frames_local_variables(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging("INFO")
    key = "re_not_a_real_key_0123456789"

    def handler(api_key: str) -> None:
        raise ValueError("the database said no")

    try:
        handler(key)
    except ValueError as error:
        # The call uvicorn makes for an unhandled exception in a request.
        logging.getLogger("uvicorn.error").error("Exception in ASGI application", exc_info=error)

    out = capsys.readouterr().out
    line = json.loads(out.strip().splitlines()[-1])
    assert line["exception"][0]["exc_type"] == "ValueError"
    assert key not in out


def test_events_below_the_configured_level_are_dropped(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging("WARNING")

    structlog.get_logger("dailyainotes.test").info("source_fetched")

    assert capsys.readouterr().out == ""
