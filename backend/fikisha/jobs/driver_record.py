"""A driver's job record, for the operator tiers (``fikisha.trust``,
operator-tiers plan T-2). Plain reads; the public surface the trust module
uses so it never imports this module's models (module boundary rule).

A driver is the ``OperatorProfile`` named on a job's current assignment.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db.models import Min
from django.utils import timezone

from fikisha.jobs.constants import JobStatus, PenaltyClass, ValueBand
from fikisha.jobs.models import CancellationRecord, Job

ELEVATED_OR_ABOVE = (ValueBand.ELEVATED, ValueBand.HIGH, ValueBand.VERY_HIGH)


def driver_record(
    operator_id: Any, *, user_id: Any = None, late_window_days: int = 30
) -> dict[str, Any]:
    """``completed_jobs`` · ``first_completed_at`` · ``elevated_completed_ids``
    (completed ELEVATED-or-above jobs) · ``driven_job_ids`` (every job they
    are or were last assigned to drive) · ``late_cancellations`` (late
    cancellations / wasted trips the operator's user made in the window)."""
    driven = Job.objects.filter(assignment__assigned_driver_profile_id=operator_id)
    completed = driven.filter(status=JobStatus.COMPLETED)
    agg = completed.aggregate(first=Min("completed_at"))
    late = 0
    if user_id is not None:
        since = timezone.now() - timedelta(days=late_window_days)
        late = (
            CancellationRecord.objects.filter(cancelled_by_user_id=user_id, created_at__gte=since)
            .exclude(penalty_class=PenaltyClass.NONE)
            .count()
        )
    return {
        "completed_jobs": completed.count(),
        "first_completed_at": agg["first"],
        "elevated_completed_ids": [
            str(i)
            for i in completed.filter(value_band__in=ELEVATED_OR_ABOVE).values_list("id", flat=True)
        ],
        "driven_job_ids": [str(i) for i in driven.values_list("id", flat=True)],
        "late_cancellations": late,
    }
