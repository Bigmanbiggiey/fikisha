"""``JobLifecycleService.transition`` — the algorithm in job-state-machine.md §2.1."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from django.db import connection

from fikisha.jobs.constants import JobEventCategory, JobStatus
from fikisha.jobs.errors import (
    GuardFailed,
    NotAuthorisedToInitiate,
    NotImplementedInThisIncrement,
    StaleJob,
    TransitionNotAllowed,
)
from fikisha.jobs.models import Job, JobEvent

pytestmark = pytest.mark.django_db


# ─── publish ─────────────────────────────────────────────────────────
def test_publish_computes_and_freezes_band(
    draft_job: Job, business_actor: Any, do_transition: Callable
) -> None:
    view = do_transition(
        draft_job,
        JobStatus.REQUESTED,
        business_actor,
        data={"initiator_tokens": ["BUSINESS_OWNER_OR_DISPATCHER"]},
    )

    assert view["status"] == JobStatus.REQUESTED
    assert view["version"] == 1
    assert view["value_band"] == "STANDARD"  # 1_200_000 minor ≤ 5_000_000
    assert view["required_trust_level"] == "L1"
    assert view["is_high_value"] is False
    assert view["config_version_id"] is not None
    assert view["timestamps"]["published_at"] is not None
    assert "CONFIRMED" in view["next_allowed_statuses"]

    draft_job.refresh_from_db()
    assert draft_job.status == JobStatus.REQUESTED


def test_publish_requires_verified_business(
    draft_job: Job, business_actor: Any, do_transition: Callable
) -> None:
    from fikisha.business.models import BusinessVerificationStatus

    draft_job.business.verification_status = BusinessVerificationStatus.UNVERIFIED
    draft_job.business.save(update_fields=["verification_status"])

    with pytest.raises(GuardFailed) as exc:
        do_transition(
            draft_job,
            JobStatus.REQUESTED,
            business_actor,
            data={"initiator_tokens": ["BUSINESS_OWNER_OR_DISPATCHER"]},
        )
    assert "business" in str(exc.value).lower()
    draft_job.refresh_from_db()
    assert draft_job.status == JobStatus.DRAFT


def test_publish_rejects_hazardous_cargo(
    draft_job: Job, business_actor: Any, do_transition: Callable
) -> None:
    draft_job.cargo.handling_flags = ["HAZARDOUS"]
    draft_job.cargo.save(update_fields=["handling_flags"])
    with pytest.raises(GuardFailed):
        do_transition(
            draft_job,
            JobStatus.REQUESTED,
            business_actor,
            data={"initiator_tokens": ["BUSINESS_OWNER_OR_DISPATCHER"]},
        )


# ─── lookup / authorisation / concurrency ────────────────────────────
def test_disallowed_transition_is_422(
    draft_job: Job, admin_actor: Any, do_transition: Callable
) -> None:
    with pytest.raises(TransitionNotAllowed):
        do_transition(draft_job, JobStatus.DELIVERED, admin_actor)
    draft_job.refresh_from_db()
    assert draft_job.status == JobStatus.DRAFT
    assert draft_job.version == 0


def test_unknown_status_is_422(draft_job: Job, admin_actor: Any, do_transition: Callable) -> None:
    with pytest.raises(TransitionNotAllowed):
        do_transition(draft_job, "TELEPORTED", admin_actor)


def test_wrong_initiator_is_403(
    draft_job: Job, business_actor: Any, do_transition: Callable
) -> None:
    # REQUESTED → FAILED is Scheduler/Admin only.
    do_transition(
        draft_job,
        JobStatus.REQUESTED,
        business_actor,
        data={"initiator_tokens": ["BUSINESS_OWNER_OR_DISPATCHER"]},
    )
    draft_job.refresh_from_db()
    with pytest.raises(NotAuthorisedToInitiate):
        do_transition(
            draft_job,
            JobStatus.FAILED,
            business_actor,
            data={"initiator_tokens": ["BUSINESS_PARTY"]},
        )


def test_if_match_mismatch_is_412(
    draft_job: Job, admin_actor: Any, do_transition: Callable
) -> None:
    with pytest.raises(StaleJob):
        do_transition(draft_job, JobStatus.REQUESTED, admin_actor, if_match=99)
    do_transition(draft_job, JobStatus.REQUESTED, admin_actor, if_match=0)  # correct version
    draft_job.refresh_from_db()
    assert draft_job.version == 1


# ─── idempotency ────────────────────────────────────────────────────
def test_idempotent_replay_returns_stored_view_without_second_effect(
    draft_job: Job, admin_actor: Any, do_transition: Callable
) -> None:
    first = do_transition(draft_job, JobStatus.REQUESTED, admin_actor, key="k-1")
    events_after_first = JobEvent.objects.filter(job=draft_job).count()

    second = do_transition(draft_job, JobStatus.REQUESTED, admin_actor, key="k-1")
    assert second == first
    assert JobEvent.objects.filter(job=draft_job).count() == events_after_first
    draft_job.refresh_from_db()
    assert draft_job.version == 1  # not bumped twice


# ─── events / audit / outbox atomicity ──────────────────────────────
def test_status_event_and_audit_and_outbox_written_together(
    draft_job: Job, admin_actor: Any, do_transition: Callable
) -> None:
    from fikisha.audit.models import AuditLogEntry
    from fikisha.audit.services import verify_chain
    from fikisha.outbox.models import OutboxEvent

    do_transition(draft_job, JobStatus.REQUESTED, admin_actor)

    ev = JobEvent.objects.get(job=draft_job, category=JobEventCategory.STATUS_TRANSITION)
    assert ev.from_status == JobStatus.DRAFT and ev.to_status == JobStatus.REQUESTED
    assert ev.seq == 1
    assert AuditLogEntry.objects.filter(
        action="job.transition.requested", entity_id=draft_job.id
    ).exists()
    assert OutboxEvent.objects.filter(
        event_type="JobRequested", aggregate_id=str(draft_job.id)
    ).exists()
    assert verify_chain() == []


def test_guard_failure_rolls_back_everything(
    draft_job: Job, business_actor: Any, do_transition: Callable
) -> None:
    from fikisha.outbox.models import OutboxEvent

    draft_job.business.verification_status = "UNVERIFIED"
    draft_job.business.save(update_fields=["verification_status"])
    outbox_before = OutboxEvent.objects.count()

    with pytest.raises(GuardFailed):
        do_transition(
            draft_job,
            JobStatus.REQUESTED,
            business_actor,
            data={"initiator_tokens": ["BUSINESS_OWNER_OR_DISPATCHER"]},
        )

    assert JobEvent.objects.filter(job=draft_job).count() == 0
    assert OutboxEvent.objects.count() == outbox_before


# ─── custody chain (assignment-eligibility guards are covered in Step 5) ──
@pytest.fixture
def _bypass_assignment_guards(monkeypatch: pytest.MonkeyPatch) -> None:
    from fikisha.jobs import guards

    for name in (
        "VehicleEligible",
        "DriverVerificationCurrent",
        "DriverTrustCeilingCoversValue",
        "HighValueApproved",
    ):
        monkeypatch.setitem(guards.GUARDS, name, lambda job, actor, ctx: None)


def test_full_custody_chain_to_delivered(
    draft_job: Job,
    admin_actor: Any,
    do_transition: Callable,
    _bypass_assignment_guards: None,
    driver_and_vehicle: tuple[Any, Any],
) -> None:
    driver, vehicle = driver_and_vehicle
    op_id = str(driver.id)
    j = draft_job
    do_transition(j, JobStatus.REQUESTED, admin_actor)
    do_transition(
        j,
        JobStatus.CONFIRMED,
        admin_actor,
        data={"agreed_price_kes": 250_000, "operator_party": "OPERATOR", "operator_id": op_id},
    )
    j.refresh_from_db()
    assert j.agreement_id is not None
    assert j.proposed_price_kes == 250_000

    do_transition(
        j,
        JobStatus.ASSIGNED,
        admin_actor,
        data={
            "driver_profile": driver,
            "vehicle": vehicle,
            "operator_party": "OPERATOR",
            "operator_id": op_id,
            "assigned_by": "ADMIN",
        },
    )
    j.refresh_from_db()
    assert j.status == JobStatus.ASSIGNED
    assert j.assignment_id is not None

    from fikisha.identity.authz.actors import actor_from_user

    driver_actor = actor_from_user(driver.user)  # custody steps are driver-initiated
    for to in (
        JobStatus.AT_PICKUP,
        JobStatus.PICKED_UP,
        JobStatus.IN_TRANSIT,
        JobStatus.AT_DESTINATION,
        JobStatus.DELIVERED,
    ):
        data: dict[str, Any] = {}
        if to == JobStatus.PICKED_UP:
            data = {"pickup_method": "BUSINESS_CONFIRM"}
        if to == JobStatus.DELIVERED:
            data = {"party_name": "J. Mwangi", "otp_verified": True, "photo_evidence_ids": ["p1"]}
        do_transition(j, to, driver_actor, data=data)
        j.refresh_from_db()
        assert j.status == to

    seqs = list(JobEvent.objects.filter(job=j).order_by("seq").values_list("seq", flat=True))
    assert seqs == list(range(1, len(seqs) + 1))  # gapless, monotonic
    assert JobEvent.objects.filter(job=j, is_custody=True).exists()
    with connection.cursor() as cur:
        cur.execute("SELECT count(*) FROM chain_of_custody WHERE job_id = %s", [str(j.id)])
        assert cur.fetchone()[0] > 0


# ─── deferred increments ───────────────────────────────────────────
def test_dispute_paths_raise_not_implemented(
    draft_job: Job,
    admin_actor: Any,
    do_transition: Callable,
    _bypass_assignment_guards: None,
    driver_and_vehicle: tuple[Any, Any],
) -> None:
    driver, vehicle = driver_and_vehicle
    op_id = str(driver.id)
    do_transition(draft_job, JobStatus.REQUESTED, admin_actor)
    do_transition(
        draft_job,
        JobStatus.CONFIRMED,
        admin_actor,
        data={"agreed_price_kes": 1, "operator_party": "OPERATOR", "operator_id": op_id},
    )
    do_transition(
        draft_job,
        JobStatus.ASSIGNED,
        admin_actor,
        data={
            "driver_profile": driver,
            "vehicle": vehicle,
            "operator_party": "OPERATOR",
            "operator_id": op_id,
        },
    )
    draft_job.refresh_from_db()
    with pytest.raises(NotImplementedInThisIncrement):
        do_transition(
            draft_job,
            JobStatus.DISPUTED,
            admin_actor,
            data={"blocking_incident_id": "x"},
        )
    draft_job.refresh_from_db()
    assert draft_job.status == JobStatus.ASSIGNED  # rolled back


# ─── DB backstop (job-state-machine.md §7) ────────────────────────
def _seed_band_raw(job: Job) -> None:
    """Raw band seed (no status change → no lifecycle trigger) so the backstop
    tests exercise the transition trigger in isolation from the
    ``ck_job_band_set_once_published`` CHECK."""
    with connection.cursor() as cur:
        cur.execute(
            "UPDATE job SET value_band = 'STANDARD', required_trust_level = 'L1' WHERE id = %s",
            [str(job.id)],
        )


def test_raw_update_along_a_disallowed_edge_is_rejected_by_trigger(draft_job: Job) -> None:
    from django.db import DatabaseError, transaction

    _seed_band_raw(draft_job)
    with pytest.raises(DatabaseError) as exc:
        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute("SELECT set_config('app.lifecycle_service', '', true)")
                cur.execute(
                    "UPDATE job SET status = 'COMPLETED' WHERE id = %s", [str(draft_job.id)]
                )
    assert "illegal job status transition" in str(exc.value)
    draft_job.refresh_from_db()
    assert draft_job.status == JobStatus.DRAFT


def test_raw_update_along_an_allowed_edge_passes_the_trigger(draft_job: Job) -> None:
    # DRAFT → REQUESTED is in allowed_job_transition, so the backstop lets a raw
    # write through even without the service GUC (the service layers guards,
    # events, audit and outbox on top — this checks only the trigger's allow-list).
    _seed_band_raw(draft_job)
    with connection.cursor() as cur:
        cur.execute("SELECT set_config('app.lifecycle_service', '', true)")
        cur.execute("UPDATE job SET status = 'REQUESTED' WHERE id = %s", [str(draft_job.id)])
    draft_job.refresh_from_db()
    assert draft_job.status == JobStatus.REQUESTED
