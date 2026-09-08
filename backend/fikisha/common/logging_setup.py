"""Structured logging configuration.

Phase 1 observability §1: JSON logs, one line per request/task, a ``request_id``
on every line, and PII kept out. This builds a stdlib ``dictConfig`` that pipes
through ``structlog`` for rendering.
"""

from __future__ import annotations

from typing import Any

import structlog

from fikisha.common.request_id import get_request_id

# Keys whose values must never be logged verbatim.
_SENSITIVE_KEYS = {
    "password",
    "secret",
    "token",
    "authorization",
    "access_token",
    "refresh_token",
    "code",
    "otp",
    "otp_code",
    "phone",
    "id_number",
    "payout_number",
    "signed_url",
}


def _add_request_id(_: Any, __: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    event_dict.setdefault("request_id", get_request_id())
    return event_dict


def _scrub(_: Any, __: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    for key in list(event_dict):
        if key.lower() in _SENSITIVE_KEYS:
            event_dict[key] = "[redacted]"
    return event_dict


_SHARED_PROCESSORS: list[Any] = [
    structlog.contextvars.merge_contextvars,
    _add_request_id,
    structlog.processors.add_log_level,
    structlog.processors.TimeStamper(fmt="iso", utc=True),
    _scrub,
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
]


def build_logging_config(*, level: str = "INFO", json_output: bool = True) -> dict[str, Any]:
    renderer = (
        structlog.processors.JSONRenderer()
        if json_output
        else structlog.dev.ConsoleRenderer(colors=False)
    )

    structlog.configure(
        processors=[
            *_SHARED_PROCESSORS,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structured": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": renderer,
                "foreign_pre_chain": _SHARED_PROCESSORS,
            }
        },
        "handlers": {
            "console": {"class": "logging.StreamHandler", "formatter": "structured"},
        },
        "root": {"handlers": ["console"], "level": level},
        "loggers": {
            "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
            "django.db.backends": {"level": "WARNING"},
        },
    }


def get_logger(name: str = "fikisha") -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
