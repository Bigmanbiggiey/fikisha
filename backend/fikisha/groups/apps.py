from __future__ import annotations

from django.apps import AppConfig


class GroupsConfig(AppConfig):
    name = "fikisha.groups"
    label = "groups"
    verbose_name = "Fikisha · Operator Groups"

    def ready(self) -> None:
        from fikisha.groups import policies  # noqa: F401  (registers authz policies)
