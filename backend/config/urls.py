"""Root URL configuration.

All application routes live under ``/api/v1/``. Liveness/readiness probes live at
the root so an orchestrator does not need auth or the API prefix.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from fikisha.observability.health import healthz, readyz

urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("readyz", readyz, name="readyz"),
    path("api/v1/", include(("fikisha.api.urls", "api"), namespace="v1")),
]

if settings.DEBUG:
    urlpatterns += [path("django-admin/", admin.site.urls)]
