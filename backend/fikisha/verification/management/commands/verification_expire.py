"""Materialise EXPIRED decisions for verification records whose expiry has passed.

Read validity is already deterministic (``VerificationRecord.effective_state``
folds expiry in) — this command only keeps the append-only decision history
complete and emits ``verification.expired`` events for a later notification
phase. Run it from cron / a scheduled task, or ad hoc:

    python manage.py verification_expire
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from fikisha.verification.tasks import expire_due


class Command(BaseCommand):
    help = "Expire verification records whose expiry date has passed."

    def handle(self, *args: Any, **options: Any) -> None:
        stats = expire_due()
        self.stdout.write(self.style.SUCCESS(f"Expired {stats['expired']} verification record(s)."))
