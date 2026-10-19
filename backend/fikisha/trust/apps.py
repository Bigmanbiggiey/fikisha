from __future__ import annotations

from django.apps import AppConfig


class TrustConfig(AppConfig):
    name = "fikisha.trust"
    label = "trust"
    verbose_name = "Fikisha · Operator tiers"

    def ready(self) -> None:
        from fikisha.trust import policies  # noqa: F401  (registers authz policies)
