from __future__ import annotations

from django.apps import AppConfig


class IdentityConfig(AppConfig):
    name = "fikisha.identity"
    label = "identity"
    verbose_name = "Fikisha · Identity & Access"

    def ready(self) -> None:
        from fikisha.identity.authz import policies  # noqa: F401  (registers policies)
