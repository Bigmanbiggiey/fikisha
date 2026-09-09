from __future__ import annotations

from django.apps import AppConfig


class VerificationConfig(AppConfig):
    name = "fikisha.verification"
    label = "verification"
    verbose_name = "Fikisha · Verification"

    def ready(self) -> None:
        from fikisha.verification import policies  # noqa: F401  (registers authz policies)
