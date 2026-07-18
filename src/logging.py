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


class _StructlogLikeFormatter(logging.Formatter):
    """Stdlib formatter that renders lines in the style of the app's structlog ``ConsoleRenderer``.

    Used for Temporal's ``workflow.logger`` (a ``LoggerAdapter`` around
    ``logging.getLogger("temporalio.workflow")``). We cannot run structlog's own processors there:
    the workflow sandbox restricts ``threading`` (structlog's ``PrintLogger.__init__`` takes a
    ``threading.Lock``) and ``datetime.now`` (structlog's ``TimeStamper``), so the real
    ProcessorFormatter raises ``RestrictedWorkflowAccessError`` inside a workflow activation.
    stdlib ``logging`` is sandbox-unrestricted, so this formatter — stdlib only — is the safe way
    to give ``workflow.logger`` output the same look as the rest of the app. The Temporal workflow
    context (workflow_id/run_id/…) the adapter attaches as ``record.temporal_workflow`` is rendered
    as a trailing ``key=value`` tail, mirroring structlog.
    """

    def __init__(self) -> None:
        super().__init__(fmt="%(asctime)s [%(levelname)-8s] %(message)s", datefmt="%Y-%m-%dT%H:%M:%S")

    def format(self, record: logging.LogRecord) -> str:
        record.levelname = record.levelname.lower()  # structlog lower-cases the level
        line = super().format(record)
        ctx = getattr(record, "temporal_workflow", None)
        if isinstance(ctx, dict) and ctx:
            tail = " ".join(f"{k}={v}" for k, v in ctx.items())
            line = f"{line}  {tail}"
        return line


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
    # Make Temporal's workflow.logger emit in the app's structlog style. The workflow sandbox can't
    # run structlog's renderer, so we attach a stdlib formatter to the workflow logger instead and
    # stop propagation so the root handler above doesn't also print the raw line.
    import temporalio.workflow as _workflow

    workflow_logger = logging.getLogger("temporalio.workflow")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_StructlogLikeFormatter())
    workflow_logger.addHandler(handler)
    workflow_logger.propagate = False
    workflow_logger.setLevel(getattr(logging, level.upper()))
    # The SDK's LoggerAdapter also appends workflow details to the message text itself
    # (workflow_info_on_message). Our formatter already renders them as a clean key=value tail from
    # record.temporal_workflow, so disable the adapter's text suffix to avoid printing them twice.
    _workflow.logger.workflow_info_on_message = False
    _CONFIGURED = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger (configuring with defaults if not yet done)."""
    if not _CONFIGURED:
        configure_logging()
    return structlog.get_logger(name)
