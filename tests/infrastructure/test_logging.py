from __future__ import annotations

import structlog

from infrastructure.logging import configure_logging, get_logger


def test_get_logger_is_loggable() -> None:
    logger = get_logger("test.module")
    # structlog.get_logger returns a lazy proxy; it must expose the log API and bind().
    assert hasattr(logger, "info") and hasattr(logger, "bind")
    bound = logger.bind(context="x")
    assert hasattr(bound, "info")


def test_configure_logging_idempotent() -> None:
    configure_logging(level="debug")
    configure_logging(level="info")  # second call must not raise
    logger = get_logger("again")
    assert hasattr(logger, "info")
    _ = structlog  # keep import referenced
