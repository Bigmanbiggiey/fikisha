"""A driver's job record, for the operator tiers (``fikisha.trust``,
operator-tiers plan T-2). Plain reads; the public surface the trust module
uses so it never imports this module's models (module boundary rule).

A driver is the ``OperatorProfile`` named on a job's current assignment.
"""

from __future__ import annotations

from typing import Any

from django.db.models import Min

from fikisha.jobs.constants import JobStatus, ValueBand
from fikisha.jobs.models import Job

ELEVATED_OR_ABOVE = (ValueBand.ELEVATED, ValueBand.HIGH, ValueBand.VERY_HIGH)


def driver_record(operator_id: Any) -> dict[str, Any]:
    """``completed_jobs`` · ``first_completed_at`` · ``elevated_completed_ids``
    (completed ELEVATED-or-above jobs) · ``driven_job_ids`` (every job they
    are or were last assigned to drive).

    No late-cancellation count: operators can't cancel a job and no-shows
    aren't recorded, so that criterion is "not yet measured" (CF-1)."""
    driven = Job.objects.filter(assignment__assigned_driver_profile_id=operator_id)
    completed = driven.filter(status=JobStatus.COMPLETED)
    agg = completed.aggregate(first=Min("completed_at"))
    return {
        "completed_jobs": completed.count(),
        "first_completed_at": agg["first"],
        "elevated_completed_ids": [
            str(i)
            for i in completed.filter(value_band__in=ELEVATED_OR_ABOVE).values_list("id", flat=True)
        ],
        "driven_job_ids": [str(i) for i in driven.values_list("id", flat=True)],
    }


def recent_driven_job_ids(operator_id: Any, *, limit: int) -> list[str]:
    """The ``limit`` jobs the driver was most recently assigned to drive."""
    return [
        str(i)
        for i in Job.objects.filter(assignment__assigned_driver_profile_id=operator_id)
        .order_by("-assigned_at", "-id")
        .values_list("id", flat=True)[:limit]
    ]


def group_completed_jobs(group_id: Any) -> int:
    """Completed jobs assigned to a group (trust-and-disputes plan A9)."""
    return Job.objects.filter(assignment__group_id=group_id, status=JobStatus.COMPLETED).count()
