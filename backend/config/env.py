"""Tiny, dependency-free environment reader.

Rationale (phase-2a-decisions ADR-2A-02): a ~40-line typed helper over
``os.environ`` avoids adding a config library while keeping settings readable and
fail-loud. Secrets are never defaulted to a usable value in production settings.
"""

from __future__ import annotations

import os
from pathlib import Path

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off", ""}


class ImproperlyConfigured(Exception):
    """Raised when a required environment variable is missing."""


def _raw(key: str, default: str | None) -> str | None:
    return os.environ.get(key, default)


def str_(key: str, default: str | None = None, *, required: bool = False) -> str:
    value = _raw(key, default)
    if value is None:
        if required:
            raise ImproperlyConfigured(f"Required environment variable {key!r} is not set")
        return ""
    return value


def bool_(key: str, default: bool = False) -> bool:
    value = _raw(key, None)
    if value is None:
        return default
    lowered = value.strip().lower()
    if lowered in _TRUE:
        return True
    if lowered in _FALSE:
        return False
    raise ImproperlyConfigured(f"Environment variable {key!r} is not a boolean: {value!r}")


def int_(key: str, default: int) -> int:
    value = _raw(key, None)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ImproperlyConfigured(
            f"Environment variable {key!r} is not an int: {value!r}"
        ) from exc


def list_(
    key: str,
    default: list[str] | None = None,
    *,
    sep: str = ",",
    required: bool = False,
) -> list[str]:
    value = _raw(key, None)
    if value is None or value.strip() == "":
        if required and not default:
            raise ImproperlyConfigured(f"Required environment variable {key!r} is not set")
        return list(default or [])
    return [item.strip() for item in value.split(sep) if item.strip()]


def path_(key: str, default: str) -> Path:
    return Path(str_(key, default))
