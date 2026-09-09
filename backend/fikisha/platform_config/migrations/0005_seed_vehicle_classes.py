"""Seed the approved initial vehicle classes (Phase 0 operator-model §2.1).

Heavy classes (CANTER, TIPPER, LORRY, SEMI_TRUCK, TRAILER) require the
HEAVY_CLASS_COMPLIANCE verification domain — the ``heavy`` flag is config data
so no vehicle-class literal ever appears in application code (ADR-2C-01).
Admin-extensible: adding a class later is a row, not a migration.
"""

from __future__ import annotations

from django.db import migrations

CLASSES = [
    ("MOTORCYCLE", "Motorcycle", "Pikipiki", False, 0),
    ("PICKUP", "Pickup", "Pikapu", False, 10),
    ("CANTER", "Canter", "Kanta", True, 20),
    ("TIPPER", "Tipper", "Tipa", True, 30),
    ("LORRY", "Lorry", "Lori", True, 40),
    ("SEMI_TRUCK", "Semi-truck", "Trela ndogo", True, 50),
    ("TRAILER", "Trailer", "Trela", True, 60),
    ("OTHER", "Other", "Nyingine", False, 99),
]


def seed(apps, schema_editor):
    VehicleClass = apps.get_model("platform_config", "VehicleClass")
    for code, en, sw, heavy, order in CLASSES:
        VehicleClass.objects.update_or_create(
            code=code,
            defaults={
                "name_en": en,
                "name_sw": sw,
                "heavy": heavy,
                "active": True,
                "sort_order": order,
            },
        )


def unseed(apps, schema_editor):
    VehicleClass = apps.get_model("platform_config", "VehicleClass")
    VehicleClass.objects.filter(code__in=[c[0] for c in CLASSES]).delete()


class Migration(migrations.Migration):
    dependencies = [("platform_config", "0004_vehicleclass")]

    operations = [migrations.RunPython(seed, unseed)]
