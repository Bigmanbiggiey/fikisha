"""Work discovery (design-phase-3-wireframes.md §7.2) — Design Phase 6
Increment 4.

**Individual-operator-only this increment** (see
``jobs.assignment_candidates`` module docstring for the founder scope
decision): matching is scoped to the actor's own directly-registered
vehicles. Group-driver discovery (``DRIVER_ACCEPTS``) is deferred alongside
the Group Manager assign flow.

**Interim, conservative matching rule** (documented as provisional, same
spirit as ADR-2D-05's interim trust rule — no route optimisation or
geo-matching, per CLAUDE.md's MVP scope): ``REQUESTED``/``NEGOTIATING`` jobs
the actor hasn't already opened a negotiation thread on, whose required
vehicle class (if any) matches one of the actor's own active vehicles'
classes. The wireframe is explicit that this must not read as "the whole
marketplace" — this is the server-side boundary that enforces that.
"""

from __future__ import annotations

from typing import Any

from fikisha.jobs import creation, guards
from fikisha.jobs.constants import JobStatus
from fikisha.jobs.errors import JobNoLongerAvailable
from fikisha.jobs.selectors import get_job
from fikisha.operators.models import OperatorProfile


def _driver_for(actor: Any) -> OperatorProfile | None:
    user = getattr(actor, "user", None)
    user_id = getattr(user, "id", None)
    if user_id is None:
        return None
    return OperatorProfile.objects.filter(user_id=user_id).order_by("created_at").first()


def open_jobs_for(actor: Any, *, value_band: str | None = None) -> Any:
    from django.db.models import Q

    from fikisha.jobs.models import Job
    from fikisha.negotiation.models import NegotiationThread
    from fikisha.vehicles.models import Vehicle

    driver = _driver_for(actor)
    if driver is None:
        return Job.objects.none()

    vehicle_class_codes = list(
        Vehicle.objects.filter(
            owner_operator_id=driver.id, deactivated_at__isnull=True
        ).values_list("vehicle_class__code", flat=True)
    )
    if not vehicle_class_codes:
        return Job.objects.none()

    class_q = Q(vehicle_requirement__isnull=True) | Q(
        vehicle_requirement__required_vehicle_class_codes=[]
    )
    for code in vehicle_class_codes:
        class_q |= Q(vehicle_requirement__required_vehicle_class_codes__contains=[code])

    already_party_job_ids = NegotiationThread.objects.filter(operator_id=driver.id).values_list(
        "job_id", flat=True
    )

    qs = (
        Job.objects.filter(status__in=[JobStatus.REQUESTED, JobStatus.NEGOTIATING])
        .exclude(id__in=already_party_job_ids)
        .filter(class_q)
        .select_related("business", "vehicle_requirement", "agreement", "assignment")
        .order_by("-created_at")
    )
    if value_band:
        qs = qs.filter(value_band=value_band)
    return qs


def opportunity_view(job: Any, actor: Any) -> dict[str, Any]:
    """``creation.job_detail()`` plus a per-job eligibility marker for the
    viewing operator, computed server-side — never left to the frontend to
    derive — reusing the exact predicates the assignment guards enforce
    (``jobs.guards._driver_verification_reasons`` /
    ``_driver_trust_reasons``)."""
    view = creation.job_detail(job)
    driver = _driver_for(actor)
    if driver is None:
        view["eligibility"] = {
            "eligible": False,
            "trust_level": "",
            "reasons": ["No operator profile."],
        }
        return view
    verification_reasons = guards._driver_verification_reasons(driver)
    level, trust_reasons = guards._driver_trust_reasons(driver, job)
    reasons = verification_reasons + trust_reasons
    view["eligibility"] = {"eligible": not reasons, "trust_level": level, "reasons": reasons}
    return view


def opportunity_detail(actor: Any, job_id: Any) -> dict[str, Any]:
    """A single job's opportunity view (Job Opportunity, §7.3) — the operator
    is not yet a negotiation party at this point, so ``job.read``'s
    ``is_job_party`` check would 403; this is deliberately a coarser read,
    gated only by the job still being open (``REQUESTED``/``NEGOTIATING``),
    matching what ``open_jobs_for`` would have listed it under."""
    job = get_job(job_id)
    if job.status not in {JobStatus.REQUESTED, JobStatus.NEGOTIATING}:
        raise JobNoLongerAvailable("This job is no longer open for a new offer.")
    return opportunity_view(job, actor)
