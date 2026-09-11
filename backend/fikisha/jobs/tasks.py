"""Scheduled maintenance sweeps (Phase 2D Step 11, plan §19 / ADR-2D-08 / Q-5).

A sweep is a **maintenance trigger, not a second business-rule engine**: it
finds candidates and hands each one to the same
:func:`fikisha.jobs.service.transition` every API view already calls — the
identical guards, apply fns, audit, and outbox wiring run either way. Nothing
here writes ``job.status`` directly, duplicates a guard's time computation
outside this module, or invents a new lifecycle transition.

Two genuine sweep candidates exist in the approved domain (see
``docs/phase-2/phase-2d-plan.md`` §19 Step 11 for the full time-dependent
inventory and why every other candidate stays lazy/request-time):

* ``expire_requests`` — ``REQUESTED`` jobs whose ``timeouts.request_expiry_hours``
  window has elapsed with no confirmed agreement, moved to ``FAILED`` via the
  existing ``(REQUESTED, FAILED)`` rule (``RequestExpired`` guard, ``SCHEDULER``
  initiator — both already part of the Increment-1 table; this sweep is the
  first caller that actually reaches them).
* ``autocomplete_delivered`` — ``DELIVERED`` jobs whose
  ``timeouts.delivery_acceptance`` window has closed (so a fresh dispute is no
  longer possible anyway) and that carry no open dispute, moved to
  ``COMPLETED`` via the existing ``(DELIVERED, COMPLETED)`` rule
  (``NoOpenBlockingDispute`` guard, ``SCHEDULER`` initiator).

The actor for both is :class:`fikisha.identity.authz.actors.SystemActor` —
the shared "scheduler / event-handler identity" (``verification.services``
has its own older, module-local ``SystemActor`` this mirrors); ``audit_role
== "SYSTEM"`` is exactly what grants the ``SCHEDULER`` initiator token
inside ``jobs.service._actor_matches``. Every write still gets the ordinary
hash-chained audit row + outbox events — no parallel "sweep audit" mechanism.

Candidates are queried in bounded batches, then handed to ``transition()``
**one at a time**, each in its own transaction (`transition()`'s own row
lock, not a second one). A candidate that another actor or worker already
moved on (or that a fresh dispute now blocks) is not a failure — the same
guard that would have refused an ordinary API caller refuses the sweep just
as cleanly, and is counted as ``skipped``. This is also what makes both
sweeps idempotent and safe under concurrent workers: two workers racing the
same job serialise on `transition()`'s ``SELECT ... FOR UPDATE``; the loser
finds the row already past ``REQUESTED``/``DELIVERED`` and gets a clean,
harmless ``TransitionNotAllowed``.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from celery import shared_task
from django.http import Http404
from django.utils import timezone

from fikisha.common.exceptions import DomainError
from fikisha.common.logging_setup import get_logger
from fikisha.identity.authz.actors import SystemActor
from fikisha.jobs.constants import JobStatus
from fikisha.jobs.models import Job
from fikisha.jobs.service import TransitionContext, transition
from fikisha.platform_config import services as cfg

log = get_logger("fikisha.jobs.sweeps")

_DEFAULT_BATCH_SIZE = 100


def _run_sweep(*, name: str, job_ids: list[Any], to: str, ctx: TransitionContext) -> dict[str, int]:
    """Shared drive loop: call ``transition()`` for each candidate, one at a
    time, classifying the outcome. A candidate a guard refuses (already
    handled, now blocked by a fresh dispute, etc.) is ``skipped``, not
    ``failed`` — that is the guard doing exactly its ordinary job."""
    changed = skipped = failed = 0
    actor = SystemActor()
    for job_id in job_ids:
        try:
            transition(job_id=job_id, to=to, actor=actor, context=ctx)
        except (DomainError, Http404) as exc:
            skipped += 1
            log.info(
                "jobs.sweep.candidate_skipped",
                sweep=name,
                job_id=str(job_id),
                reason=type(exc).__name__,
            )
        except Exception:  # a single bad candidate must not abort the whole sweep
            failed += 1
            log.exception("jobs.sweep.candidate_failed", sweep=name, job_id=str(job_id))
        else:
            changed += 1
    stats = {"candidates": len(job_ids), "changed": changed, "skipped": skipped, "failed": failed}
    if job_ids:
        log.info("jobs.sweep.completed", sweep=name, **stats)
    return stats


def _request_expiry_candidates(batch_size: int) -> list[Any]:
    hours = float(cfg.get("timeouts.request_expiry_hours", 24) or 24)
    cutoff = timezone.now() - timedelta(hours=hours)
    return list(
        Job.objects.filter(
            status=JobStatus.REQUESTED, published_at__isnull=False, published_at__lte=cutoff
        )
        .order_by("published_at")
        .values_list("id", flat=True)[:batch_size]
    )


@shared_task(name="fikisha.jobs.tasks.expire_requests")
def expire_requests(batch_size: int = _DEFAULT_BATCH_SIZE) -> dict[str, int]:
    """``REQUESTED`` jobs past ``timeouts.request_expiry_hours`` with no
    agreement → ``FAILED`` (``FailureRecord.reason_text ==
    "EXPIRED_NO_OFFER"``, per ``apply_fns.fail``'s existing default — no new
    domain code). ``ctx["expiry_reached"]`` is what the ``RequestExpired``
    guard checks; this sweep is the one place that is allowed to set it,
    because it is the one place that actually computed the window."""
    job_ids = _request_expiry_candidates(batch_size)
    ctx = TransitionContext(data={"expiry_reached": True})
    return _run_sweep(name="expire_requests", job_ids=job_ids, to=JobStatus.FAILED, ctx=ctx)


def _delivery_acceptance_candidates(batch_size: int) -> list[Any]:
    from fikisha.incidents.constants import DisputeStatus
    from fikisha.incidents.models import Dispute

    windows = cfg.get("timeouts.delivery_acceptance", {}) or {}
    standard_hours = float(windows.get("standard_hours", 24))
    high_hours = float(windows.get("high_hours", 48))
    now = timezone.now()

    # An open dispute already blocks the guard at transition time — excluded
    # here purely so a disputed job doesn't show up as a noisy "skipped"
    # candidate every sweep run, not because the exclusion is load-bearing.
    open_dispute_job_ids = Dispute.objects.exclude(status=DisputeStatus.RESOLVED).values("job_id")

    base = Job.objects.filter(status=JobStatus.DELIVERED, delivered_at__isnull=False).exclude(
        id__in=open_dispute_job_ids
    )
    standard = base.filter(
        is_high_value=False, delivered_at__lte=now - timedelta(hours=standard_hours)
    )
    high = base.filter(is_high_value=True, delivered_at__lte=now - timedelta(hours=high_hours))
    ids = list(standard.order_by("delivered_at").values_list("id", flat=True)[:batch_size])
    ids += list(high.order_by("delivered_at").values_list("id", flat=True)[:batch_size])
    return ids[:batch_size]


@shared_task(name="fikisha.jobs.tasks.autocomplete_delivered")
def autocomplete_delivered(batch_size: int = _DEFAULT_BATCH_SIZE) -> dict[str, int]:
    """``DELIVERED`` jobs whose delivery-acceptance window has closed with no
    open dispute → ``COMPLETED`` (the same ``complete`` apply fn an explicit
    business/recipient confirmation uses — including the same idempotent
    ``CommissionRecord`` creation, same audit, same outbox events)."""
    job_ids = _delivery_acceptance_candidates(batch_size)
    return _run_sweep(
        name="autocomplete_delivered",
        job_ids=job_ids,
        to=JobStatus.COMPLETED,
        ctx=TransitionContext(),
    )
