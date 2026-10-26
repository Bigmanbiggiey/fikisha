"""Seed the resume transitions into ``allowed_job_transition`` (trust-and-
disputes plan B1, ADR-2D-54): DISPUTED back to its recorded pre-dispute
state. Listed here, not imported from ``jobs.transitions``, so the migration
stays fixed whatever the code later says.
"""

from __future__ import annotations

from django.db import migrations

_PAIRS = [
    ("DISPUTED", "ASSIGNED"),
    ("DISPUTED", "AT_PICKUP"),
    ("DISPUTED", "PICKED_UP"),
    ("DISPUTED", "IN_TRANSIT"),
    ("DISPUTED", "AT_DESTINATION"),
    ("DISPUTED", "DELIVERED"),
]


def _seed(apps, schema_editor):
    model = apps.get_model("jobs", "AllowedJobTransition")
    model.objects.bulk_create(
        [model(from_status=f, to_status=t) for f, t in _PAIRS], ignore_conflicts=True
    )


def _unseed(apps, schema_editor):
    model = apps.get_model("jobs", "AllowedJobTransition")
    for f, t in _PAIRS:
        model.objects.filter(from_status=f, to_status=t).delete()


class Migration(migrations.Migration):
    dependencies = [("jobs", "0018_flag_review_append_only")]

    operations = [migrations.RunPython(_seed, _unseed)]
