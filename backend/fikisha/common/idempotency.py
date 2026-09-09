"""Minimal idempotency for retsafe POST creates (Phase 1 ADR-008; Phase 2B brief §26).

A client may send an ``Idempotency-Key`` header on a create. The first request
runs normally and its response (status + JSON body) is cached, keyed by
``(key, actor, method, path)``. A replay with the same key returns the cached
response instead of creating a second row. A concurrent replay while the first
is still in flight gets ``409 idempotency_in_progress``.

This is a small, self-contained extension of the foundation — it does not depend
on a request/response framework beyond DRF's ``Response``.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import Any

from django.core.cache import cache
from rest_framework.request import Request
from rest_framework.response import Response

from fikisha.common.exceptions import ConflictError

_TTL_SECONDS = 24 * 60 * 60
_LOCK_TTL_SECONDS = 60
_HEADER = "HTTP_IDEMPOTENCY_KEY"


def _cache_key(raw_key: str, *, actor_id: str, method: str, path: str) -> str:
    digest = hashlib.sha256(f"{actor_id}\n{method}\n{path}\n{raw_key}".encode()).hexdigest()
    return f"idem:{digest}"


def idempotent(request: Request, *, actor_id: str, run: Callable[[], Response]) -> Response:
    """Run ``run()`` at most once per ``Idempotency-Key`` for this actor + path."""
    raw_key = request.META.get(_HEADER, "").strip()
    if not raw_key:
        return run()
    if len(raw_key) > 200:
        raise ConflictError("Idempotency-Key is too long.", code="idempotency_key_invalid")

    key = _cache_key(raw_key, actor_id=actor_id, method=request.method or "", path=request.path)
    cached: dict[str, Any] | None = cache.get(key)
    if cached is not None:
        if cached.get("pending"):
            raise ConflictError(
                "A request with this Idempotency-Key is still being processed.",
                code="idempotency_in_progress",
            )
        response = Response(cached["body"], status=cached["status"])
        response["Idempotency-Replayed"] = "true"
        return response

    if not cache.add(key, {"pending": True}, _LOCK_TTL_SECONDS):
        raise ConflictError(
            "A request with this Idempotency-Key is still being processed.",
            code="idempotency_in_progress",
        )

    response = run()
    if 200 <= response.status_code < 300:
        cache.set(key, {"status": response.status_code, "body": response.data}, _TTL_SECONDS)
    else:
        cache.delete(key)  # let the client retry a failed create
    return response
