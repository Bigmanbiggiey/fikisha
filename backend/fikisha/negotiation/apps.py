from __future__ import annotations

from django.apps import AppConfig


class NegotiationConfig(AppConfig):
    name = "fikisha.negotiation"
    label = "negotiation"
    verbose_name = "Fikisha · Negotiation"

    def ready(self) -> None:
        from fikisha.negotiation import policies  # noqa: F401  (registers authz policies)
