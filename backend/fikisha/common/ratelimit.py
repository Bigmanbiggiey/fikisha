"""Cache-backed rate limiting.

Phase 2A ships a fixed-window limiter over the Django cache (Redis in
compose, locmem in tests). Phase 1 security-architecture §1.7 targets a Redis
token bucket — that refinement is a Phase 2B item (see phase-2a-decisions
ADR-2A-05). Auth/OTP limiters **fail closed**: if the cache is unreachable the
call is denied rather than allowed.
"""

from __future__ import annotations

import time

from django.core.cache import cache

from fikisha.common.exceptions import RateLimitedError


class RateLimiter:
    def __init__(self, *, scope: str, limit: int, window_seconds: int, fail_closed: bool = True):
        self.scope = scope
        self.limit = limit
        self.window_seconds = window_seconds
        self.fail_closed = fail_closed

    def _key(self, identifier: str) -> str:
        bucket = int(time.time() // self.window_seconds)
        return f"rl:{self.scope}:{identifier}:{bucket}"

    def check(self, identifier: str) -> None:
        """Raise :class:`RateLimitedError` if ``identifier`` has exceeded the limit."""
        key = self._key(identifier)
        try:
            added = cache.add(key, 0, timeout=self.window_seconds + 1)
            current = cache.incr(key) if not added else cache.incr(key)
        except Exception as exc:
            if self.fail_closed:
                raise RateLimitedError(
                    "Rate-limit backend unavailable.", retry_after=self.window_seconds
                ) from exc
            return
        if current > self.limit:
            raise RateLimitedError(retry_after=self.window_seconds)

    def peek(self, identifier: str) -> int:
        try:
            return int(cache.get(self._key(identifier), 0))
        except Exception:
            return 0
