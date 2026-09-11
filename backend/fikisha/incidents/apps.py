from __future__ import annotations

from django.apps import AppConfig


class IncidentsConfig(AppConfig):
    name = "fikisha.incidents"
    label = "incidents"
    verbose_name = "Fikisha · Incidents & Disputes"

    def ready(self) -> None:
        from fikisha.incidents import policies  # noqa: F401  (registers authz policies)
