"""Store every plate in its display form: capitals, single spaces (assessment
2026-10-19, part 1). ``registration_normalized`` is unchanged by this, since it
was already uppercased with spaces removed."""

from __future__ import annotations

from typing import Any

from django.db import migrations


def uppercase_registrations(apps: Any, schema_editor: Any) -> None:
    Vehicle = apps.get_model("vehicles", "Vehicle")
    for vehicle in Vehicle.objects.only("id", "registration").iterator():
        shown = " ".join((vehicle.registration or "").upper().split())
        if shown != vehicle.registration:
            Vehicle.objects.filter(pk=vehicle.pk).update(registration=shown)


class Migration(migrations.Migration):
    dependencies = [("vehicles", "0001_initial")]

    operations = [migrations.RunPython(uppercase_registrations, migrations.RunPython.noop)]
