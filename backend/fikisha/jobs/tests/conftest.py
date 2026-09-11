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
        BusinessMembership,
        BusinessRole,
        BusinessVerificationStatus,
        MembershipStatus,
    )

    biz = BusinessAccount.objects.create(
        owner_user=user,
        trading_name="Kitengela Traders",
        verification_status=BusinessVerificationStatus.VERIFIED,
    )
    BusinessMembership.objects.create(
        business=biz, user=user, role=BusinessRole.OWNER, status=MembershipStatus.ACTIVE
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


# ─── assignment increment (§19 Step 5) fixtures ──────────────────────
@pytest.fixture
def verify_subject(db: Any) -> Callable[..., None]:
    """``verify_subject(operator_or_vehicle, "IDENTITY", "LICENCE", ...)`` — writes
    VERIFIED verification records with no expiry."""
    from fikisha.operators.models import OperatorProfile
    from fikisha.vehicles.models import Vehicle
    from fikisha.verification.models import State, VerificationRecord

    def _verify(subject: Any, *domains: str) -> None:
        if isinstance(subject, OperatorProfile):
            kw = {"subject_type": "OPERATOR", "subject_operator": subject}
        elif isinstance(subject, Vehicle):
            kw = {"subject_type": "VEHICLE", "subject_vehicle": subject}
        else:  # pragma: no cover
            raise TypeError(type(subject).__name__)
        for domain in domains:
            VerificationRecord.objects.update_or_create(
                domain=domain, defaults={"state": State.VERIFIED, "expires_at": None}, **kw
            )

    return _verify


@pytest.fixture
def make_verified_operator(db: Any, make_user: Any, verify_subject: Callable) -> Callable[..., Any]:
    from fikisha.operators.models import OperatorProfile, OperatorStatus

    def _make(phone: str, name: str, *, verified: bool = True) -> Any:
        prof = OperatorProfile.objects.create(
            user=make_user(phone), full_name=name, status=OperatorStatus.ACTIVE
        )
        if verified:
            verify_subject(prof, "IDENTITY", "LICENCE", "GOOD_CONDUCT")
        return prof

    return _make


@pytest.fixture
def make_vehicle(db: Any, verify_subject: Callable) -> Callable[..., Any]:
    from fikisha.platform_config.models import VehicleClass
    from fikisha.vehicles.models import Vehicle, VehicleStatus

    def _make(
        *,
        owner_operator: Any = None,
        owner_group: Any = None,
        heavy: bool = False,
        capacity_value: int = 2000,
        registration: str = "KDA 001A",
        verified: bool = True,
        status: str = VehicleStatus.ACTIVE,
        volume_m3: Any = None,
        feature_tags: list[str] | None = None,
    ) -> Any:
        vclass = VehicleClass.objects.filter(active=True, heavy=heavy).first()
        if vclass is None:
            vclass = VehicleClass.objects.create(
                code="HEAVY_TEST" if heavy else "LIGHT_TEST",
                name_en="Test",
                name_sw="Test",
                heavy=heavy,
            )
        v = Vehicle.objects.create(
            owner_operator=owner_operator,
            owner_group=owner_group,
            vehicle_class=vclass,
            registration=registration,
            capacity_value=capacity_value,
            volume_m3=volume_m3,
            feature_tags=feature_tags or [],
            status=status,
        )
        if verified:
            domains = ["VEHICLE", "ASSOCIATION"] + (["HEAVY_CLASS_COMPLIANCE"] if heavy else [])
            verify_subject(v, *domains)
        return v

    return _make


@pytest.fixture
def eligible_driver(make_verified_operator: Callable) -> Any:
    return make_verified_operator("+254733200001", "D. Kamau")


@pytest.fixture
def eligible_vehicle(make_vehicle: Callable, eligible_driver: Any) -> Any:
    return make_vehicle(owner_operator=eligible_driver, registration="KDA 200B")


@pytest.fixture
def make_confirmed_job(
    db: Any, verified_business: Any, user: Any, admin_actor: Any
) -> Callable[..., Job]:
    """``make_confirmed_job(operator=prof)`` or ``(group=grp)`` -> a CONFIRMED job
    (driven DRAFT->REQUESTED->CONFIRMED via the lifecycle service)."""
    from fikisha.jobs.constants import OperatorParty

    def _make(
        *,
        operator: Any = None,
        group: Any = None,
        declared_value_kes: int = 1_200_000,
        proposed_price_kes: int = 250_000,
        min_payload_kg: int = 500,
        required_vehicle_class_codes: list[str] | None = None,
        latent_risk_cargo: bool = False,
    ) -> Job:
        cargo = CargoDetails.objects.create(
            description="cargo", declared_value_kes=declared_value_kes, handling_flags=[]
        )
        pickup = JobLocation.objects.create(type="PICKUP", source_kind="AD_HOC", address_text="A")
        dest = JobLocation.objects.create(
            type="DESTINATION", source_kind="AD_HOC", address_text="B"
        )
        vreq = VehicleRequirement.objects.create(
            min_payload_kg=min_payload_kg,
            required_vehicle_class_codes=required_vehicle_class_codes or [],
        )
        job = Job.objects.create(
            business=verified_business,
            created_by=user,
            status=JobStatus.DRAFT,
            pickup_location=pickup,
            destination_location=dest,
            cargo=cargo,
            vehicle_requirement=vreq,
            proposed_price_kes=proposed_price_kes,
            declared_value_kes=declared_value_kes,
            latent_risk_cargo=latent_risk_cargo,
        )
        transition(
            job_id=job.id,
            to=JobStatus.REQUESTED,
            actor=admin_actor,
            context=TransitionContext(data={"initiator_tokens": ["ADMIN"]}),
        )
        party = OperatorParty.OPERATOR if operator is not None else OperatorParty.GROUP
        transition(
            job_id=job.id,
            to=JobStatus.CONFIRMED,
            actor=admin_actor,
            context=TransitionContext(
                data={
                    "initiator_tokens": ["ADMIN"],
                    "operator_party": party,
                    "operator_id": str(operator.id) if operator is not None else None,
                    "group_id": str(group.id) if group is not None else None,
                    "agreed_price_kes": proposed_price_kes,
                    "accepting_entry_ids": [],
                }
            ),
        )
        job.refresh_from_db()
        return job

    return _make


@pytest.fixture
def actor_for() -> Callable[[Any], Any]:
    from fikisha.identity.authz.actors import actor_from_user

    return actor_from_user


@pytest.fixture
def make_assigned_job(
    db: Any,
    make_confirmed_job: Callable,
    eligible_driver: Any,
    eligible_vehicle: Any,
    actor_for: Callable,
) -> Callable[..., Any]:
    """``make_assigned_job(declared_value_kes=..., pickup_contact_phone=...,
    recipient_phone=...)`` -> an ASSIGNED job with a verified driver + vehicle."""
    from fikisha.jobs.assignment import assign_job

    def _make(
        *,
        declared_value_kes: int = 1_200_000,
        pickup_contact_phone: str = "+254700900001",
        recipient_phone: str = "+254700900002",
    ) -> Any:
        job = make_confirmed_job(operator=eligible_driver, declared_value_kes=declared_value_kes)
        if pickup_contact_phone is not None:
            job.pickup_location.contact_phone = pickup_contact_phone
            job.pickup_location.save(update_fields=["contact_phone"])
        job.recipient_phone = recipient_phone or ""
        job.save(update_fields=["recipient_phone"])
        # STANDARD -> operator self-assigns; ELEVATED+ -> an admin assigns with
        # the interim trust-ceiling override (ADR-2D-05: L2/L3 are unreachable).
        job.refresh_from_db()
        if job.value_band == "STANDARD":
            assign_job(
                actor=actor_for(eligible_driver.user),
                job_id=job.id,
                driver_profile_id=eligible_driver.id,
                vehicle_id=eligible_vehicle.id,
            )
        else:
            from fikisha.identity.models import AdminProfile, AdminRole, RoleAssignment, User

            admin_user = User.objects.create_user(phone="+254700900777", is_staff=True)
            AdminProfile.objects.create(user=admin_user, active=True)
            RoleAssignment.objects.create(user=admin_user, role=AdminRole.PLATFORM_ADMIN)
            assign_job(
                actor=actor_for(admin_user),
                job_id=job.id,
                driver_profile_id=eligible_driver.id,
                vehicle_id=eligible_vehicle.id,
                admin_override_reason="test: interim trust-ceiling override",
            )
        job.refresh_from_db()
        return job

    return _make


@pytest.fixture
def driver_actor(eligible_driver: Any, actor_for: Callable) -> Any:
    return actor_for(eligible_driver.user)


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
