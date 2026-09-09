"""Seed the single pilot zone.

D-PIL-5: the founder's Kitengela zone breakdown is deferred, so the pilot area
is one zone until it is supplied. This is the documented pilot baseline, not
production data.
"""

from __future__ import annotations

from django.db import migrations

PILOT_ZONE = {
    "code": "KITENGELA",
    "name_en": "Kitengela and environs",
    "name_sw": "Kitengela na maeneo jirani",
    "active": True,
    "sort_order": 0,
}


def seed(apps, schema_editor):
    Zone = apps.get_model("platform_config", "Zone")
    Zone.objects.update_or_create(code=PILOT_ZONE["code"], defaults=PILOT_ZONE)


def unseed(apps, schema_editor):
    Zone = apps.get_model("platform_config", "Zone")
    Zone.objects.filter(code=PILOT_ZONE["code"]).delete()


class Migration(migrations.Migration):
    dependencies = [("platform_config", "0002_zone")]

    operations = [migrations.RunPython(seed, unseed)]
