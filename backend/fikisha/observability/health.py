"""Health / readiness probes.

* ``GET /healthz``       — liveness: 200 if the process is up. No dependencies.
* ``GET /readyz``        — readiness: checks DB + cache. 200 / 503.
* ``GET /api/v1/health/``— the API-namespaced readiness check (Phase 2A brief §15).

None of these expose infrastructure detail (hostnames, versions, credentials) —
only ``ok`` / ``fail`` per dependency.
"""

from __future__ import annotations

from django.core.cache import cache
from django.db import connections
from django.http import HttpRequest, JsonResponse
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


def _check_db() -> bool:
    try:
        with connections["default"].cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return True
    except Exception:
        return False


def _check_cache() -> bool:
    try:
        cache.set("health:ping", "1", timeout=5)
        return cache.get("health:ping") == "1"
    except Exception:
        return False


def healthz(_request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})


def readyz(_request: HttpRequest) -> JsonResponse:
    checks = {"database": _check_db(), "cache": _check_cache()}
    healthy = all(checks.values())
    return JsonResponse(
        {"status": "ok" if healthy else "degraded", "checks": checks},
        status=200 if healthy else 503,
    )


class ApiHealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    @extend_schema(
        responses={
            200: OpenApiResponse(description="Healthy"),
            503: OpenApiResponse(description="A dependency is unavailable"),
        }
    )
    def get(self, _request: Request) -> Response:
        checks = {"database": _check_db(), "cache": _check_cache()}
        healthy = all(checks.values())
        return Response(
            {"status": "ok" if healthy else "degraded", "checks": checks},
            status=200 if healthy else 503,
        )
