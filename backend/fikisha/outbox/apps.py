from __future__ import annotations

from django.apps import AppConfig


class OutboxConfig(AppConfig):
    name = "fikisha.outbox"
    label = "outbox"
    verbose_name = "Fikisha · Transactional outbox"

    def ready(self) -> None:
        # Import handler registrations so decorators run.
        from fikisha.outbox import handlers  # noqa: F401
