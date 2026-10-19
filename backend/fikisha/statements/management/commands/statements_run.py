"""``manage.py statements_run [--period-start YYYY-MM-DD]`` — bill one finished
week now (default: last week). Calls the Celery task function directly, like
``jobs_expire_requests``."""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from fikisha.statements.tasks import run_weekly_statements


class Command(BaseCommand):
    help = "Generate commission statements for one finished Mon-Sun week."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--period-start", dest="period_start", default=None)

    def handle(self, *args: Any, **options: Any) -> None:
        result = run_weekly_statements(options["period_start"])
        self.stdout.write(
            f"{result['period_start']}..{result['period_end']}: "
            f"{result['statements_created']} created, "
            f"{result['payees_skipped_existing']} skipped"
        )
