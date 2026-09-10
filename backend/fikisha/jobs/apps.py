from __future__ import annotations

from django.apps import AppConfig


class JobsConfig(AppConfig):
    name = "fikisha.jobs"
    label = "jobs"
    verbose_name = "Fikisha · Jobs & coordination"

    def ready(self) -> None:
        from fikisha.jobs import policies  # noqa: F401  (registers authz policies)
