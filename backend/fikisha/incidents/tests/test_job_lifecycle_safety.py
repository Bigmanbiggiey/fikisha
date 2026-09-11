"""The incident/dispute system must never become a second Job-status writer.

* No incidents code path sets ``job.status`` directly — every DISPUTED-related
  transition goes through ``JobLifecycleService.transition()``.
* The dispute guards re-verify their ``ctx`` claims against real, persisted
  rows — a forged ``ctx`` claim (no real Incident / Resolution) is refused.
* ``NoOpenBlockingDispute`` blocks ordinary completion while a dispute is open.
* No new transition was added merely for convenience — the transitions table
  is unchanged by Step 8 (dispute/resolve rows pre-existed from Increment 1).
"""

from __future__ import annotations

import ast
import inspect
from collections.abc import Callable
from typing import Any

import pytest

from fikisha.incidents import services as incidents_services
from fikisha.incidents.constants import IncidentType
from fikisha.incidents.services import open_dispute, report_incident, resolve_dispute
from fikisha.jobs import apply_fns
from fikisha.jobs.constants import JobStatus
from fikisha.jobs.errors import GuardFailed, JobNoLongerAvailable
from fikisha.jobs.service import TransitionContext
from fikisha.jobs.service import transition as job_transition

pytestmark = pytest.mark.django_db


def test_incidents_services_module_never_assigns_job_status() -> None:
    """Static check: no ``... .status = ...`` assignment targets a ``job``-named
    variable anywhere in the service module (the only legitimate ``job.status``
    writer is ``fikisha.jobs.service.transition``)."""
    source = inspect.getsource(incidents_services)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Attribute)
                    and target.attr == "status"
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "job"
                ):
                    pytest.fail(
                        f"incidents.services assigns job.status directly at line {node.lineno}"
                    )


def test_apply_fns_dispute_paths_are_noop_not_a_second_writer() -> None:
    """``freeze`` / ``freeze_post_completion`` / ``resolve_failed`` /
    ``resolve_cancelled`` are aliases of the existing ``noop`` apply fn — the
    job-side write is exactly the status write the engine already performs;
    nothing incidents-specific happens inside ``jobs.apply_fns``.
    ``resolve_completed`` is the one exception — it shares Step 9's real
    ``complete`` (commission) body, not ``noop`` (see
    ``fikisha.jobs.tests.test_commission_completion`` for its own coverage of
    that path, including the post-completion-dispute idempotency case)."""
    for name in ("freeze", "freeze_post_completion", "resolve_failed", "resolve_cancelled"):
        assert apply_fns.APPLY[name] is apply_fns.noop
    assert apply_fns.APPLY["resolve_completed"] is apply_fns.APPLY["complete"]
    assert apply_fns.APPLY["complete"] is not apply_fns.noop


def test_a_forged_blocking_incident_id_is_refused(
    make_assigned_job: Callable, admin_actor: Any
) -> None:
    """Calling the engine directly (bypassing ``incidents.services``) with a
    made-up ``blocking_incident_id`` must not freeze the job — the guard
    re-verifies against a real, persisted Incident."""
    job = make_assigned_job()
    with pytest.raises(GuardFailed):
        job_transition(
            job_id=job.id,
            to=JobStatus.DISPUTED,
            actor=admin_actor,
            context=TransitionContext(
                data={
                    "initiator_tokens": [],
                    "blocking_incident_id": "00000000-0000-0000-0000-000000000000",
                }
            ),
        )
    job.refresh_from_db()
    assert job.status == JobStatus.ASSIGNED


def test_a_forged_resolution_id_is_refused(
    make_assigned_job: Callable, business_owner_actor: Any, admin_actor: Any
) -> None:
    job = make_assigned_job()
    incident = report_incident(actor=business_owner_actor, job_id=job.id, type=IncidentType.LOSS)
    open_dispute(actor=business_owner_actor, job_id=job.id, incident_ids=[incident.id])
    with pytest.raises(GuardFailed):
        job_transition(
            job_id=job.id,
            to=JobStatus.COMPLETED,
            actor=admin_actor,
            context=TransitionContext(
                data={
                    "initiator_tokens": [],
                    "resolution_id": "00000000-0000-0000-0000-000000000000",
                    "routed_job_status": JobStatus.COMPLETED,
                }
            ),
        )
    job.refresh_from_db()
    assert job.status == JobStatus.DISPUTED


def test_a_resolution_for_a_different_job_cannot_resolve_this_one(
    make_assigned_job: Callable, business_owner_actor: Any, admin_actor: Any
) -> None:
    job_a = make_assigned_job()
    job_b = make_assigned_job()
    incident_a = report_incident(
        actor=business_owner_actor, job_id=job_a.id, type=IncidentType.LOSS
    )
    incident_b = report_incident(
        actor=business_owner_actor, job_id=job_b.id, type=IncidentType.LOSS
    )
    dispute_a, _va = open_dispute(
        actor=business_owner_actor, job_id=job_a.id, incident_ids=[incident_a.id]
    )
    open_dispute(actor=business_owner_actor, job_id=job_b.id, incident_ids=[incident_b.id])

    resolution_a, _ = resolve_dispute(
        actor=admin_actor,
        dispute_id=dispute_a.id,
        outcome_code="AMICABLE_AGREEMENT",
        rationale="resolves job A only",
        routed_job_status=JobStatus.COMPLETED,
    )
    # Try to use job A's resolution to resolve job B's dispute via the raw engine.
    with pytest.raises(GuardFailed):
        job_transition(
            job_id=job_b.id,
            to=JobStatus.COMPLETED,
            actor=admin_actor,
            context=TransitionContext(
                data={
                    "initiator_tokens": [],
                    "resolution_id": str(resolution_a.id),
                    "routed_job_status": JobStatus.COMPLETED,
                }
            ),
        )
    job_b.refresh_from_db()
    assert job_b.status == JobStatus.DISPUTED


def test_no_open_blocking_dispute_prevents_ordinary_completion(
    make_assigned_job: Callable, business_owner_actor: Any, admin_actor: Any
) -> None:
    """``(DELIVERED, COMPLETED)`` carries ``NoOpenBlockingDispute`` — an open
    dispute must block ordinary completion, even though ``complete`` itself
    remains deferred to Step 9 (the guard still runs first)."""
    job = make_assigned_job()
    incident = report_incident(actor=business_owner_actor, job_id=job.id, type=IncidentType.LOSS)
    open_dispute(actor=business_owner_actor, job_id=job.id, incident_ids=[incident.id])
    job.refresh_from_db()
    assert job.status == JobStatus.DISPUTED
    # DISPUTED -> DELIVERED is not a legal transition either way; the guard
    # itself is exercised directly to confirm it rejects an open dispute.
    from fikisha.jobs.guards import no_open_blocking_dispute

    with pytest.raises(JobNoLongerAvailable):
        no_open_blocking_dispute(job, admin_actor, {})


def test_disputed_to_resume_prior_does_not_exist(
    make_assigned_job: Callable, admin_actor: Any
) -> None:
    """RESUME / RESUME_PRIOR is explicitly not implemented (ADR-2D-07, E-1
    stays OPEN) — the pre-dispute status is never an allowed transition target
    from DISPUTED."""
    from fikisha.jobs.transitions import rule_for

    job = make_assigned_job()
    assert rule_for(JobStatus.DISPUTED, JobStatus.ASSIGNED) is None
    assert job.status == JobStatus.ASSIGNED  # sanity: this *was* the pre-dispute status


def test_resolution_routed_status_check_constraint_excludes_resume(
    make_assigned_job: Callable,
) -> None:
    """DB-level backstop: even bypassing every service and guard, no Resolution
    row can be persisted with a ``routed_job_status`` outside
    ``{COMPLETED, FAILED, CANCELLED}``."""
    from django.db import IntegrityError, transaction

    from fikisha.incidents.models import Dispute, Resolution

    job = make_assigned_job()
    dispute = Dispute.objects.create(job=job, incident_ids=[], pre_dispute_status=job.status)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Resolution.objects.create(
                dispute=dispute,
                outcome_code="ADMIN_DETERMINATION",
                rationale="attempting to route to ASSIGNED",
                routed_job_status="ASSIGNED",
                resolved_by_admin=job.created_by,
            )
