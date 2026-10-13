"""JSON logs for every process, one object per line on stdout.

Our own events go through structlog. Logs from libraries (uvicorn, Alembic, SQLAlchemy) pass
through the same formatter, so every line a container writes has the same shape.
"""

import logging
import sys

import structlog
from structlog.typing import Processor

from dailyainotes.settings import LogLevel


def configure_logging(level: LogLevel) -> None:
    shared: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]
    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
    # Uvicorn installs its own text handlers at startup; send its records to ours instead.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True
    # Uvicorn's access lines start with the client's address, and logs never keep raw IPs
    # (INTENT.md). Caddy's log records each request without it.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
