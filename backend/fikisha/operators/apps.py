from __future__ import annotations

from django.apps import AppConfig


class OperatorsConfig(AppConfig):
    name = "fikisha.operators"
    label = "operators"
    verbose_name = "Fikisha · Operators"

    def ready(self) -> None:
        from fikisha.operators import policies  # noqa: F401  (registers authz policies)
