"""``If-Match`` optimistic concurrency at the HTTP layer (ADR-2D-44;
`api-architecture.md` "Concurrency", ADR-2D-02).

The domain layer has had the check since Increment 1:
``JobLifecycleService.transition()`` raises ``StaleJob`` (412) when
``TransitionContext.if_match_version`` differs from ``job.version``. Nothing
fed it from HTTP. Rather than thread a version through every service that
ends in a transition (custody, assignment, cancel, staff actions...), this
middleware notes the header for the job named in the URL, and
``transition()`` takes it, once, for that job:

- only on unsafe methods of a URL with a ``job_id`` kwarg;
- only for the job in the URL (a transition on any other job is unaffected);
- consumed by the first transition, so an action that legitimately makes
  two transitions doesn't trip over its own first write.

A missing header is still accepted (see ADR-2D-44 on making it mandatory).
``*`` means "any version". A malformed value is 400 ``invalid_if_match``,
raised when the transition reads it.
"""

from __future__ import annotations

from collections.abc import Callable
from contextvars import ContextVar
from typing import Any

from django.http import HttpRequest, HttpResponse
from rest_framework import status

from fikisha.common.exceptions import DomainError

_SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
_pending: ContextVar[dict[str, str] | None] = ContextVar("fikisha_if_match", default=None)


class InvalidIfMatch(DomainError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "invalid_if_match"
    default_detail = 'If-Match must be the job version in quotes, for example "7".'


class IfMatchMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        token = _pending.set({})
        try:
            return self.get_response(request)
        finally:
            _pending.reset(token)

    def process_view(
        self, request: HttpRequest, view_func: Any, view_args: Any, view_kwargs: dict[str, Any]
    ) -> None:
        raw = request.META.get("HTTP_IF_MATCH")
        job_id = view_kwargs.get("job_id")
        holder = _pending.get()
        if (
            raw
            and job_id is not None
            and request.method not in _SAFE_METHODS
            and holder is not None
        ):
            holder["job_id"] = str(job_id)
            holder["raw"] = raw


def parse(raw: str) -> int | None:
    """``"7"``, ``W/"7"`` or ``7`` → 7; ``*`` → None (any version)."""
    value = raw.strip()
    if value == "*":
        return None
    if value.startswith("W/"):
        value = value[2:]
    value = value.strip('"')
    if not value.isdigit():
        raise InvalidIfMatch()
    return int(value)


def take_expected_version(job_id: Any) -> int | None:
    """The version this request's ``If-Match`` expects for ``job_id``, or
    None. Read once: the first transition of that job consumes it."""
    holder = _pending.get()
    if not holder or holder.get("job_id") != str(job_id):
        return None
    raw = holder.pop("raw")
    holder.pop("job_id")
    return parse(raw)


def etag(version: int) -> str:
    return f'"{version}"'
