"""List stored phone numbers that break the Kenyan rule (assessment
2026-10-20 L-3, LD-2). Read-only: nothing is changed. Numbers are masked.

    python manage.py phones_report
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from django.core.management.base import BaseCommand

from fikisha.identity.phone import is_valid_phone, mask_phone


class Command(BaseCommand):
    help = "List stored phone numbers that are not valid Kenyan numbers (read-only)."

    def handle(self, *args: Any, **options: Any) -> None:
        from fikisha.business.models import BusinessAccount, BusinessLocation
        from fikisha.identity.models import User
        from fikisha.jobs.models import Job, JobLocation
        from fikisha.operators.models import OperatorProfile

        sources: list[tuple[str, Iterable[tuple[Any, str]]]] = [
            ("user.phone", User.objects.values_list("id", "phone")),
            ("business.contact_phone", BusinessAccount.objects.values_list("id", "contact_phone")),
            (
                "business_location.contact_phone",
                BusinessLocation.objects.values_list("id", "contact_phone"),
            ),
            ("job_location.contact_phone", JobLocation.objects.values_list("id", "contact_phone")),
            ("job.recipient_phone", Job.objects.values_list("id", "recipient_phone")),
            (
                "operator_profile.phones",
                (
                    (pk, phone)
                    for pk, phones in OperatorProfile.objects.values_list("id", "phones")
                    for phone in (phones or [])
                ),
            ),
        ]
        bad = 0
        for label, rows in sources:
            for pk, phone in rows:
                if phone and not is_valid_phone(phone):
                    bad += 1
                    self.stdout.write(f"{label}\t{pk}\t{mask_phone(phone)}")
        style = self.style.SUCCESS if bad == 0 else self.style.WARNING
        self.stdout.write(style(f"{bad} stored number(s) break the rule."))
