"""Fixtures for the Phase 2D jobs engine tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.jobs.constants import JobStatus
from fikisha.jobs.models import CargoDetails, Job, JobLocation, VehicleRequirement
from fikisha.jobs.service import TransitionContext, transition


@pytest.fixture
def verified_business(db: Any, user: Any) -> Any:
    from fikisha.business.models import (
        BusinessAccount,
        BusinessLocation,
        BusinessVerificationStatus,
    )

    biz = BusinessAccount.objects.create(
        owner_user=user,
        trading_name="Kitengela Traders",
        verification_status=BusinessVerificationStatus.VERIFIED,
    )
    BusinessLocation.objects.create(business=biz, label="Main", type="MAIN")
    return biz


@pytest.fixture
def draft_job(db: Any, verified_business: Any, user: Any) -> Job:
    """A complete DRAFT job — ready for ``DRAFT → REQUESTED``."""
    cargo = CargoDetails.objects.create(
        description="20 cartons bottled water", declared_value_kes=1_200_000, handling_flags=[]
    )
    pickup = JobLocation.objects.create(type="PICKUP", source_kind="AD_HOC", address_text="Depot")
    dest = JobLocation.objects.create(
        type="DESTINATION", source_kind="AD_HOC", address_text="Shop 4, Kitengela"
    )
    vreq = VehicleRequirement.objects.create(min_payload_kg=500, required_vehicle_class_codes=[])
    return Job.objects.create(
        business=verified_business,
        created_by=user,
        status=JobStatus.DRAFT,
        pickup_location=pickup,
        destination_location=dest,
        cargo=cargo,
        vehicle_requirement=vreq,
        proposed_price_kes=250_000,
        declared_value_kes=1_200_000,
    )


@pytest.fixture
def driver_and_vehicle(db: Any, make_user: Any) -> tuple[Any, Any]:
    """A minimal (not verification-checked) driver profile + active vehicle, for
    engine tests that bypass the assignment-eligibility guards (covered in the
    assignment increment, plan §19 Step 5)."""
    from fikisha.operators.models import OperatorProfile, OperatorStatus
    from fikisha.platform_config.models import VehicleClass
    from fikisha.vehicles.models import Vehicle, VehicleStatus

    driver_user = make_user("+254733000111")
    driver = OperatorProfile.objects.create(
        user=driver_user, full_name="D. Otieno", status=OperatorStatus.ACTIVE
    )
    vclass = VehicleClass.objects.filter(active=True, heavy=False).first()
    vehicle = Vehicle.objects.create(
        owner_operator=driver,
        vehicle_class=vclass,
        registration="KDA 123X",
        capacity_value=1000,
        status=VehicleStatus.ACTIVE,
    )
    return driver, vehicle


@pytest.fixture
def admin_actor(platform_admin: Any) -> Any:
    from fikisha.identity.authz.actors import actor_from_user

    return actor_from_user(platform_admin)


@pytest.fixture
def business_actor(user: Any) -> Any:
    from fikisha.identity.authz.actors import actor_from_user

    return actor_from_user(user)


@pytest.fixture
def do_transition() -> Callable[..., dict[str, Any]]:
    """``do_transition(job, "REQUESTED", actor, data={...}, if_match=None, key="")``."""

    def _go(
        job: Job,
        to: str,
        actor: Any,
        *,
        data: dict[str, Any] | None = None,
        if_match: int | None = None,
        key: str = "",
    ) -> dict[str, Any]:
        return transition(
            job_id=job.id,
            to=to,
            actor=actor,
            context=TransitionContext(data=data or {}, if_match_version=if_match),
            idempotency_key=key,
        )

    return _go
