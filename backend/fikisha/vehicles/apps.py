from __future__ import annotations

from django.apps import AppConfig


class VehiclesConfig(AppConfig):
    name = "fikisha.vehicles"
    label = "vehicles"
    verbose_name = "Fikisha · Vehicles"

    def ready(self) -> None:
        from fikisha.vehicles import policies  # noqa: F401  (registers authz policies)
