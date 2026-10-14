from __future__ import annotations

from django.apps import AppConfig


class AdminConsoleConfig(AppConfig):
    name = "fikisha.admin_console"
    label = "admin_console"
    verbose_name = "Fikisha · Platform Admin console"

    def ready(self) -> None:
        from fikisha.admin_console import policies  # noqa: F401  (registers authz policies)
