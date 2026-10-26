"""Switch a live configuration to the commission split (founder decision
2026-10-22, ADR-2D-55): 5% from the business and 5% from the operator, no
minimum or cap.

A database that has no live configuration yet does nothing here: it is
bootstrapped from the new defaults on first use. One that has the old
``FLAT_WITH_MIN_CAP`` block gets a new config version replacing the whole
``commission`` section, audited like any other change. The values are
written out here, not read from ``defaults``, so the migration stays fixed
whatever the code later says.

It calls the real config service (versioning, hash-chained audit, outbox
event); that is safe because a database with a live configuration has run
every earlier migration of the apps it touches (see ``dependencies``).
Reversing does nothing: the old model is no longer implemented, and
historical config versions are kept.
"""

from __future__ import annotations

from django.db import migrations

_SPLIT = {"model": "SPLIT_FLAT", "business_rate": 0.05, "operator_rate": 0.05}


def _switch(apps, schema_editor):  # type: ignore[no-untyped-def]
    from fikisha.platform_config import services

    services.replace_section(
        key="commission",
        value=_SPLIT,
        changed_by=None,
        rationale=(
            "Commission split (founder decision 2026-10-22, ADR-2D-55): 5% from the "
            "business and 5% from the operator, no minimum or cap."
        ),
        source_channel="CLI",
    )


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0020_commission_split"),
        ("platform_config", "0005_seed_vehicle_classes"),
        ("audit", "0004_alter_auditlogentry_actor_role"),
        ("outbox", "0001_initial"),
    ]

    operations = [migrations.RunPython(_switch, migrations.RunPython.noop)]
