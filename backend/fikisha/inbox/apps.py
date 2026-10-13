from __future__ import annotations

from django.apps import AppConfig


class InboxConfig(AppConfig):
    name = "fikisha.inbox"
    label = "inbox"
    verbose_name = "Fikisha · Messages inbox"

    def ready(self) -> None:
        from fikisha.inbox import policies  # noqa: F401  (registers authz policies)
