"""Request / correlation id plumbing.

Every request gets an ``X-Request-ID`` (honoured from the client if present and
well-formed, otherwise generated). It is stored in a context var so the logging
config and any background task spawned from the request can include it.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from contextvars import ContextVar

from django.http import HttpRequest, HttpResponse

_request_id: ContextVar[str] = ContextVar("request_id", default="-")
_VALID = re.compile(r"^[A-Za-z0-9._\-]{8,128}$")

HEADER = "X-Request-ID"
META_KEY = "HTTP_X_REQUEST_ID"


def get_request_id() -> str:
    return _request_id.get()


def set_request_id(value: str) -> object:
    return _request_id.set(value)


def reset_request_id(token: object) -> None:
    _request_id.reset(token)  # type: ignore[arg-type]


def new_request_id() -> str:
    return uuid.uuid4().hex


class RequestIDMiddleware:
    """Bind a request id for the lifetime of the request and echo it on the response."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        incoming = request.META.get(META_KEY, "")
        rid = incoming if _VALID.match(incoming) else new_request_id()
        token = set_request_id(rid)
        request.request_id = rid  # type: ignore[attr-defined]
        try:
            response = self.get_response(request)
        finally:
            reset_request_id(token)
        response[HEADER] = rid
        return response
