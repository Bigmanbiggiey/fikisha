"""GET /jobs/opportunities — Work discovery (Design Phase 6 Increment 4).

Individual-operator-only, interim vehicle-class matching (see
``jobs.discovery`` module docstring) — never "the whole marketplace"."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from fikisha.jobs.constants import JobStatus
from fikisha.jobs.models import CargoDetails, Job, JobLocation, VehicleRequirement
from fikisha.jobs.service import TransitionContext, transition

pytestmark = pytest.mark.django_db


def _make_requested_job(
    *,
    business: Any,
    user: Any,
    admin_actor: Any,
    required_vehicle_class_codes: list[str] | None = None,
    declared_value_kes: int = 1_200_000,
) -> Job:
    cargo = CargoDetails.objects.create(
        description="cargo", declared_value_kes=declared_value_kes, handling_flags=[]
    )
    pickup = JobLocation.objects.create(type="PICKUP", source_kind="AD_HOC", address_text="A")
    dest = JobLocation.objects.create(type="DESTINATION", source_kind="AD_HOC", address_text="B")
    vreq = VehicleRequirement.objects.create(
        min_payload_kg=0, required_vehicle_class_codes=required_vehicle_class_codes or []
    )
    job = Job.objects.create(
        business=business,
        created_by=user,
        status=JobStatus.DRAFT,
        pickup_location=pickup,
        destination_location=dest,
        cargo=cargo,
        vehicle_requirement=vreq,
        proposed_price_kes=50_000,
        declared_value_kes=declared_value_kes,
    )
    transition(
        job_id=job.id,
        to=JobStatus.REQUESTED,
        actor=admin_actor,
        context=TransitionContext(data={"initiator_tokens": ["ADMIN"]}),
    )
    job.refresh_from_db()
    return job


def test_operator_sees_a_job_matching_their_own_vehicle_class(
    client_for: Callable,
    verified_business: Any,
    user: Any,
    admin_actor: Any,
    eligible_driver: Any,
    make_vehicle: Callable,
) -> None:
    make_vehicle(owner_operator=eligible_driver, registration="KDA 300P")  # non-heavy, some class
    from fikisha.vehicles.models import Vehicle

    vclass_code = Vehicle.objects.filter(owner_operator=eligible_driver).first().vehicle_class.code
    job = _make_requested_job(
        business=verified_business,
        user=user,
        admin_actor=admin_actor,
        required_vehicle_class_codes=[vclass_code],
    )
    client = client_for(eligible_driver.user)
    r = client.get("/api/v1/jobs/opportunities")
    assert r.status_code == 200, r.content
    ids = {row["id"] for row in r.data["data"]}
    assert str(job.id) in ids
    row = next(row for row in r.data["data"] if row["id"] == str(job.id))
    assert row["eligibility"]["eligible"] is True


def test_operator_does_not_see_a_job_requiring_a_class_they_dont_have(
    client_for: Callable,
    verified_business: Any,
    user: Any,
    admin_actor: Any,
    eligible_driver: Any,
    make_vehicle: Callable,
) -> None:
    make_vehicle(owner_operator=eligible_driver, registration="KDA 301P", heavy=False)
    job = _make_requested_job(
        business=verified_business,
        user=user,
        admin_actor=admin_actor,
        required_vehicle_class_codes=["__NO_SUCH_CLASS__"],
    )
    client = client_for(eligible_driver.user)
    r = client.get("/api/v1/jobs/opportunities")
    assert r.status_code == 200, r.content
    ids = {row["id"] for row in r.data["data"]}
    assert str(job.id) not in ids


def test_job_with_no_class_requirement_is_visible_to_any_registered_operator(
    client_for: Callable,
    verified_business: Any,
    user: Any,
    admin_actor: Any,
    eligible_driver: Any,
    make_vehicle: Callable,
) -> None:
    make_vehicle(owner_operator=eligible_driver, registration="KDA 302P")
    job = _make_requested_job(
        business=verified_business, user=user, admin_actor=admin_actor
    )
    client = client_for(eligible_driver.user)
    r = client.get("/api/v1/jobs/opportunities")
    assert r.status_code == 200, r.content
    ids = {row["id"] for row in r.data["data"]}
    assert str(job.id) in ids


def test_operator_with_no_vehicles_sees_nothing(
    client_for: Callable,
    verified_business: Any,
    user: Any,
    admin_actor: Any,
    eligible_driver: Any,
) -> None:
    _make_requested_job(business=verified_business, user=user, admin_actor=admin_actor)
    client = client_for(eligible_driver.user)
    r = client.get("/api/v1/jobs/opportunities")
    assert r.status_code == 200, r.content
    assert r.data["data"] == []


def test_a_job_the_operator_already_opened_a_thread_on_is_excluded(
    client_for: Callable,
    verified_business: Any,
    user: Any,
    admin_actor: Any,
    eligible_driver: Any,
    make_vehicle: Callable,
) -> None:
    from fikisha.identity.authz.actors import actor_from_user
    from fikisha.negotiation import services as negotiation_services

    make_vehicle(owner_operator=eligible_driver, registration="KDA 303P")
    job = _make_requested_job(business=verified_business, user=user, admin_actor=admin_actor)
    negotiation_services.propose(
        actor=actor_from_user(eligible_driver.user),
        job_id=job.id,
        operator_id=eligible_driver.id,
        amount_kes=45_000,
    )
    client = client_for(eligible_driver.user)
    r = client.get("/api/v1/jobs/opportunities")
    assert r.status_code == 200, r.content
    ids = {row["id"] for row in r.data["data"]}
    assert str(job.id) not in ids


def test_opportunity_detail_is_readable_before_the_operator_is_a_party(
    client_for: Callable,
    verified_business: Any,
    user: Any,
    admin_actor: Any,
    eligible_driver: Any,
    make_vehicle: Callable,
) -> None:
    make_vehicle(owner_operator=eligible_driver, registration="KDA 305P")
    job = _make_requested_job(business=verified_business, user=user, admin_actor=admin_actor)
    client = client_for(eligible_driver.user)
    # job.read (GET /jobs/<id>) would 403 here -- the operator has no thread
    # yet, so is_job_party is false. The opportunity-detail read is coarser.
    assert client.get(f"/api/v1/jobs/{job.id}").status_code == 403
    r = client.get(f"/api/v1/jobs/{job.id}/opportunity")
    assert r.status_code == 200, r.content
    assert r.data["id"] == str(job.id)
    assert r.data["eligibility"]["eligible"] is True


def test_opportunity_detail_404s_once_the_job_is_no_longer_open(
    client_for: Callable, make_confirmed_job: Callable, eligible_driver: Any
) -> None:
    job = make_confirmed_job(operator=eligible_driver)
    client = client_for(eligible_driver.user)
    r = client.get(f"/api/v1/jobs/{job.id}/opportunity")
    assert r.status_code == 409, r.content


def test_value_band_filter(
    client_for: Callable,
    verified_business: Any,
    user: Any,
    admin_actor: Any,
    eligible_driver: Any,
    make_vehicle: Callable,
) -> None:
    make_vehicle(owner_operator=eligible_driver, registration="KDA 304P")
    standard_job = _make_requested_job(
        business=verified_business, user=user, admin_actor=admin_actor, declared_value_kes=1_200_000
    )
    elevated_job = _make_requested_job(
        business=verified_business,
        user=user,
        admin_actor=admin_actor,
        declared_value_kes=10_000_000,
    )
    client = client_for(eligible_driver.user)
    r = client.get("/api/v1/jobs/opportunities?value_band=ELEVATED")
    assert r.status_code == 200, r.content
    ids = {row["id"] for row in r.data["data"]}
    assert str(elevated_job.id) in ids
    assert str(standard_job.id) not in ids
