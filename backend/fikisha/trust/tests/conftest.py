"""The jobs engine fixtures (verified operators, vehicles, confirmed jobs)
plus a quick way to give a driver a job record."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone

from fikisha.jobs.tests.conftest import *  # noqa: F403  (re-export fixtures)


@pytest.fixture
def give_jobs(
    verified_business: Any, user: Any, make_vehicle: Callable
) -> Callable[..., list[Any]]:
    """``give_jobs(driver, n, days_ago=20, status="COMPLETED", band="STANDARD")``
    -> ``n`` jobs the driver drove, written directly (insert, not a status
    change, so no lifecycle transition is involved)."""
    from fikisha.jobs.models import (
        Assignment,
        CargoDetails,
        Job,
        JobLocation,
        VehicleRequirement,
    )

    vehicles: dict[str, Any] = {}

    def _give(
        driver: Any,
        n: int,
        *,
        days_ago: int = 20,
        status: str = "COMPLETED",
        band: str = "STANDARD",
    ) -> list[Any]:
        vehicle = vehicles.get(str(driver.id))
        if vehicle is None:
            vehicle = make_vehicle(
                owner_operator=driver, registration=f"KDB {len(vehicles):03d}T", verified=False
            )
            vehicles[str(driver.id)] = vehicle
        when = timezone.now() - timedelta(days=days_ago)
        jobs = []
        for _ in range(n):
            job = Job.objects.create(
                business=verified_business,
                created_by=user,
                status=status,
                pickup_location=JobLocation.objects.create(
                    type="PICKUP", source_kind="AD_HOC", address_text="A"
                ),
                destination_location=JobLocation.objects.create(
                    type="DESTINATION", source_kind="AD_HOC", address_text="B"
                ),
                cargo=CargoDetails.objects.create(
                    description="c", declared_value_kes=0, handling_flags=[]
                ),
                vehicle_requirement=VehicleRequirement.objects.create(min_payload_kg=1),
                value_band=band,
                required_trust_level="L1",
                completed_at=when if status == "COMPLETED" else None,
            )
            assignment = Assignment.objects.create(
                job=job,
                operator_party="OPERATOR",
                operator=driver,
                assigned_driver_profile=driver,
                vehicle=vehicle,
                assigned_by="SELF",
                driver_trust_level="L1",
            )
            job.assignment = assignment
            job.save(update_fields=["assignment"])
            jobs.append(job)
        return jobs

    return _give


@pytest.fixture
def stepped_admin(admin_actor: Any) -> Any:
    import dataclasses

    return dataclasses.replace(admin_actor, is_step_up_fresh=True)
