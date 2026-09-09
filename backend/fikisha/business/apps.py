from __future__ import annotations

from django.apps import AppConfig


class BusinessConfig(AppConfig):
    name = "fikisha.business"
    label = "business"
    verbose_name = "Fikisha · Business"

    def ready(self) -> None:
        from fikisha.business import policies  # noqa: F401  (registers authz policies)
