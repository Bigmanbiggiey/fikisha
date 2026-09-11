"""``manage.py jobs_expire_requests`` — run the request-expiry sweep once
(operational recovery / manual re-run / cron fallback; Celery Beat runs the
identical task on a schedule)."""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from fikisha.jobs.tasks import expire_requests


class Command(BaseCommand):
    help = "Fail REQUESTED jobs whose request-expiry window has elapsed with no agreement."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--batch-size", type=int, default=100)

    def handle(self, *args: Any, **options: Any) -> None:
        stats = expire_requests(batch_size=options["batch_size"])
        self.stdout.write(self.style.SUCCESS(f"jobs_expire_requests: {stats}"))
