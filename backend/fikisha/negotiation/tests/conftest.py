"""Fixtures for the Phase 2D negotiation increment tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest


@pytest.fixture
def _actor() -> Callable[[Any], Any]:
    from fikisha.identity.authz.actors import actor_from_user

    return actor_from_user


@pytest.fixture
def business_owner(db: Any, make_user: Any) -> Any:
    return make_user("+254720000001")


@pytest.fixture
def verified_business(db: Any, business_owner: Any, _actor: Callable) -> Any:
    from fikisha.business.models import BusinessLocation, BusinessVerificationStatus
    from fikisha.business.services import create_business

    biz = create_business(actor=_actor(business_owner), trading_name="Kitengela Traders")
    biz.verification_status = BusinessVerificationStatus.VERIFIED
    biz.save(update_fields=["verification_status"])
    BusinessLocation.objects.create(business=biz, label="Main", type="MAIN")
    return biz


@pytest.fixture
def requested_job(db: Any, verified_business: Any, business_owner: Any, _actor: Callable) -> Any:
    """A published job in REQUESTED with a posted price of 250,000 (minor units)."""
    from fikisha.jobs.constants import JobStatus
    from fikisha.jobs.models import CargoDetails, Job, JobLocation, VehicleRequirement
    from fikisha.jobs.service import TransitionContext, transition

    cargo = CargoDetails.objects.create(
        description="20 cartons", declared_value_kes=1_200_000, handling_flags=[]
    )
    pickup = JobLocation.objects.create(type="PICKUP", source_kind="AD_HOC", address_text="Depot")
    dest = JobLocation.objects.create(type="DESTINATION", source_kind="AD_HOC", address_text="Shop")
    vreq = VehicleRequirement.objects.create(min_payload_kg=500, required_vehicle_class_codes=[])
    job = Job.objects.create(
        business=verified_business,
        created_by=business_owner,
        status=JobStatus.DRAFT,
        pickup_location=pickup,
        destination_location=dest,
        cargo=cargo,
        vehicle_requirement=vreq,
        proposed_price_kes=250_000,
        declared_value_kes=1_200_000,
    )
    transition(
        job_id=job.id,
        to=JobStatus.REQUESTED,
        actor=_actor(business_owner),
        context=TransitionContext(data={"initiator_tokens": ["BUSINESS_OWNER_OR_DISPATCHER"]}),
    )
    job.refresh_from_db()
    return job


@pytest.fixture
def make_operator(db: Any, make_user: Any) -> Callable[[str, str], Any]:
    from fikisha.operators.models import OperatorProfile, OperatorStatus

    def _make(phone: str, name: str) -> Any:
        u = make_user(phone)
        p = OperatorProfile.objects.create(user=u, full_name=name, status=OperatorStatus.ACTIVE)
        return p

    return _make


@pytest.fixture
def operator_a(make_operator: Callable) -> Any:
    return make_operator("+254730000001", "A. Otieno")


@pytest.fixture
def operator_b(make_operator: Callable) -> Any:
    return make_operator("+254730000002", "B. Wanjiru")


@pytest.fixture
def owner_actor(business_owner: Any, _actor: Callable) -> Any:
    return _actor(business_owner)
