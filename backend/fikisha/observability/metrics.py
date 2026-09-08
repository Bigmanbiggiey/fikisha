"""Metric-hook seam.

Phase 2A: a no-op counter/timing API that logs. A real backend (Prometheus
client, or the pilot ``analytics_event`` pipeline) plugs in here without callers
changing. See docs/phase-1/observability.md.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from time import perf_counter

from fikisha.common.logging_setup import get_logger

_log = get_logger("fikisha.metrics")


def increment(name: str, value: int = 1, **tags: str) -> None:
    _log.debug("metric.increment", metric=name, value=value, **tags)


def gauge(name: str, value: float, **tags: str) -> None:
    _log.debug("metric.gauge", metric=name, value=value, **tags)


@contextmanager
def timing(name: str, **tags: str) -> Iterator[None]:
    start = perf_counter()
    try:
        yield
    finally:
        _log.debug(
            "metric.timing", metric=name, ms=round((perf_counter() - start) * 1000, 2), **tags
        )
