"""Domain errors + the RFC 9457 ``application/problem+json`` exception handler.

Phase 1 api-architecture §1: the API returns ``{type, title, status, code,
detail, errors}`` where ``code`` is a stable machine string the client
localizes. No stack traces or internal detail reach the client.
"""

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException, AuthenticationFailed, NotAuthenticated
from rest_framework.response import Response

from fikisha.common.request_id import get_request_id

# NOTE: ``rest_framework.views`` is imported lazily inside the handler. Importing
# it at module load eagerly resolves DRF's ``DEFAULT_AUTHENTICATION_CLASSES``,
# which pulls this project's auth class back in before apps finish loading
# (a circular import during ``apps.populate()``).

PROBLEM_CONTENT_TYPE = "application/problem+json"


class DomainError(APIException):
    """Base class for Fikisha domain errors. Subclasses set ``code`` + ``status_code``."""

    status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_code = "domain_error"
    default_detail = "The request could not be completed."

    def __init__(self, detail: str | None = None, *, code: str | None = None) -> None:
        super().__init__(detail or self.default_detail)
        self.code = code or self.default_code


class ConflictError(DomainError):
    status_code = status.HTTP_409_CONFLICT
    default_code = "conflict"
    default_detail = "The request conflicts with the current state."


class RateLimitedError(DomainError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_code = "rate_limited"
    default_detail = "Too many requests. Please retry later."

    def __init__(self, detail: str | None = None, *, retry_after: int | None = None) -> None:
        super().__init__(detail)
        self.retry_after = retry_after


class AuthorizationError(DomainError):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "authz.forbidden"
    default_detail = "You are not permitted to perform this action."


_TITLES = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    409: "Conflict",
    412: "Precondition Failed",
    422: "Unprocessable Entity",
    429: "Too Many Requests",
    500: "Internal Server Error",
}


def _field_errors(data: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if isinstance(data, dict):
        for field, msgs in data.items():
            msgs_list = msgs if isinstance(msgs, list) else [msgs]
            for msg in msgs_list:
                code = getattr(msg, "code", None) or "invalid"
                out.append({"field": field, "code": str(code), "detail": str(msg)})
    elif isinstance(data, list):
        for msg in data:
            out.append({"field": None, "code": "invalid", "detail": str(msg)})
    return out


def problem_detail_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    from rest_framework.views import exception_handler as drf_exception_handler

    # Normalise a few Django-native exceptions DRF would otherwise 500.
    if isinstance(exc, Http404):
        exc = _as_api(status.HTTP_404_NOT_FOUND, "not_found", "Resource not found.")
    elif isinstance(exc, DjangoPermissionDenied):
        exc = AuthorizationError(str(exc) or None)
    elif isinstance(exc, DjangoValidationError):
        exc = _as_api(status.HTTP_400_BAD_REQUEST, "validation_error", "Invalid input.")

    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    http_status = response.status_code
    code = _extract_code(exc)
    detail = _extract_detail(response.data)
    body: dict[str, Any] = {
        "type": f"https://fikisha.co.ke/problems/{code}",
        "title": _TITLES.get(http_status, "Error"),
        "status": http_status,
        "code": code,
        "detail": detail,
        "request_id": get_request_id(),
    }
    field_errors = _field_errors(response.data)
    if field_errors:
        body["errors"] = field_errors

    new = Response(body, status=http_status, content_type=PROBLEM_CONTENT_TYPE)
    if isinstance(exc, RateLimitedError) and exc.retry_after is not None:
        new["Retry-After"] = str(exc.retry_after)
    if isinstance(exc, NotAuthenticated | AuthenticationFailed):
        new["WWW-Authenticate"] = 'Bearer realm="fikisha"'
    return new


def _as_api(code_status: int, code: str, detail: str) -> APIException:
    e = APIException(detail)
    e.status_code = code_status
    e.default_code = code
    return e


_GENERIC_CODES = {"invalid", "error", "parse_error"}


def _extract_code(exc: Exception) -> str:
    if isinstance(exc, DomainError):
        return exc.code
    # DRF stashes an explicit ``code=`` on the ErrorDetail carried by ``.detail``.
    detail = getattr(exc, "detail", None)
    detail_code = getattr(detail, "code", None)
    if isinstance(detail_code, str) and detail_code not in _GENERIC_CODES:
        return detail_code
    code = getattr(exc, "default_code", None) or getattr(exc, "code", None)
    return str(code) if code else "error"


def _extract_detail(data: Any) -> str:
    if isinstance(data, dict) and "detail" in data:
        return str(data["detail"])
    if isinstance(data, list) and data:
        return str(data[0])
    return "The request could not be completed."
