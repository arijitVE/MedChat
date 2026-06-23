# shared/logger.py — Structured JSON logging (request_id, doc_id, stage-wise logs)
# Used across all pipelines for observability.
#
# Every stage calls log_stage() at exit with the required observability fields
# from blueprint Section 3:
#   All stages:     job_id, stage, duration_ms, status (success | error)
#   + stage-specific extra fields passed as **kwargs

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


def _configure_structlog() -> None:
    """Configure structlog for JSON output once at module load time.

    Uses structlog's stdlib integration so logs are compatible with
    standard Python logging infrastructure (handlers, formatters, etc.).
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Set root logger to INFO so structlog messages are not suppressed
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)


# Configure once on import
_configure_structlog()


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger for the given module/component name.

    Args:
        name: Logger name, typically __name__ of the calling module.

    Returns:
        A bound structured logger that outputs JSON.

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("starting stage", job_id="abc-123", stage="ocr")
    """
    return structlog.get_logger(name)


def log_stage(
    logger: structlog.stdlib.BoundLogger,
    *,
    stage: str,
    job_id: str,
    duration_ms: float,
    status: str,
    **extra_fields: Any,
) -> None:
    """Emit a structured log entry at stage exit.

    This is the single function all pipeline stages call for their exit log.
    It enforces the mandatory observability fields defined in blueprint
    Section 3 (job_id, stage, duration_ms, status) and passes through any
    stage-specific extra fields.

    Args:
        logger: The bound structlog logger for the calling module.
        stage: Stage name (e.g. "ingestion", "llm_extraction",
               "normalization", "conflict_resolution", "worker").
        job_id: Unique job identifier.
        duration_ms: Stage execution time in milliseconds.
        status: "success" or "error".
        **extra_fields: Stage-specific observability fields, e.g.:
            LLM:        attempt_count, field_count, fallback_used, llm_latency_ms
            Conflict:   job_status, total_field_count
            Worker:     total_pipeline_latency_ms, retry_count, final_status

    Example:
        >>> log_stage(
        ...     logger,
        ...     stage="llm_extraction",
        ...     job_id="abc-123",
        ...     duration_ms=1245.3,
        ...     status="success",
        ...     field_count=12,
        ...     llm_latency_ms=1245.3,
        ... )
    """
    log_data: dict[str, Any] = {
        "stage": stage,
        "job_id": job_id,
        "duration_ms": round(duration_ms, 2),
        "status": status,
        **extra_fields,
    }

    if status == "error":
        logger.error("stage_completed", **log_data)
    else:
        logger.info("stage_completed", **log_data)
