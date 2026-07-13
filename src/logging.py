"""Structured logging setup.

Central ``structlog`` configuration used across all layers. Call :func:`configure_logging` once at
process start (worker, API). Individual modules obtain a logger via :func:`get_logger`.
"""

from __future__ import annotations

import logging
import sys
from typing import Literal

import structlog

LogLevel = Literal["debug", "info", "warning", "error", "critical"]
_CONFIGURED = False


def configure_logging(level: LogLevel = "info") -> None:
    """Configure structlog + stdlib logging once. Safe to call multiple times."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper())),
        cache_logger_on_first_use=True,
    )
    _CONFIGURED = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger (configuring with defaults if not yet done)."""
    if not _CONFIGURED:
        configure_logging()
    return structlog.get_logger(name)
