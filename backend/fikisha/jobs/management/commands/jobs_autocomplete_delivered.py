"""``manage.py jobs_autocomplete_delivered`` — run the delivery-acceptance
auto-complete sweep once (operational recovery / manual re-run / cron
fallback; Celery Beat runs the identical task on a schedule)."""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from fikisha.jobs.tasks import autocomplete_delivered


class Command(BaseCommand):
    help = (
        "Complete DELIVERED jobs whose delivery-acceptance window has closed "
        "with no open dispute."
    )

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--batch-size", type=int, default=100)

    def handle(self, *args: Any, **options: Any) -> None:
        stats = autocomplete_delivered(batch_size=options["batch_size"])
        self.stdout.write(self.style.SUCCESS(f"jobs_autocomplete_delivered: {stats}"))
