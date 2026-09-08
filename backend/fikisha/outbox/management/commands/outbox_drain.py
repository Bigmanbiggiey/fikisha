"""``manage.py outbox_drain`` — run the publisher once (used by the smoke test)."""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from fikisha.outbox.tasks import drain_outbox


class Command(BaseCommand):
    help = "Publish one batch of pending outbox events synchronously."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--batch-size", type=int, default=100)

    def handle(self, *args: Any, **options: Any) -> None:
        stats = drain_outbox(batch_size=options["batch_size"])
        self.stdout.write(self.style.SUCCESS(f"outbox drained: {stats}"))
