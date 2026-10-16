from __future__ import annotations

from django.apps import AppConfig


class StatementsConfig(AppConfig):
    name = "fikisha.statements"
    label = "statements"
    verbose_name = "Fikisha · Commission statements"

    def ready(self) -> None:
        from fikisha.statements import policies  # noqa: F401  (registers authz policies)
