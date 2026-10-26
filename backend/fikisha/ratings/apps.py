from __future__ import annotations

from django.apps import AppConfig


class RatingsConfig(AppConfig):
    name = "fikisha.ratings"
    label = "ratings"
    verbose_name = "Fikisha · Ratings"

    def ready(self) -> None:
        from fikisha.ratings import policies  # noqa: F401  (registers authz policies)
