"""Job facts for ratings (trust-and-disputes plan A4). Plain reads; the
ratings module's view of jobs (module boundary rule).

The rating window counts only time a job spends in COMPLETED: it pauses
while the job is DISPUTED and stops for good once it ends FAILED or
CANCELLED (TE-1). Worked out from the job's status-transition events, so it
is exact and testable with an explicit ``now``.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fikisha.jobs.constants import JobEventCategory, JobStatus
from fikisha.jobs.models import Job, JobEvent


def rating_subjects(job: Job) -> dict[str, Any]:
    """Who each side's rating is about, from the job's assignment: the
    business; the assigned driver's profile; the group if the assignment
    was the group's."""
    assignment = getattr(job, "assignment", None)
    return {
        "business_id": job.business_id,
        "driver_profile_id": getattr(assignment, "assigned_driver_profile_id", None),
        "group_id": getattr(assignment, "group_id", None),
    }


def time_in_completed(job_ids: list[Any], *, now: datetime) -> dict[str, timedelta]:
    """``{job_id: total time in COMPLETED up to now}`` for each job."""
    out: dict[str, timedelta] = {str(j): timedelta(0) for j in job_ids}
    started: dict[str, datetime] = {}
    events = (
        JobEvent.objects.filter(job_id__in=job_ids, category=JobEventCategory.STATUS_TRANSITION)
        .order_by("job_id", "seq")
        .values_list("job_id", "from_status", "to_status", "server_time")
    )
    for job_id, from_status, to_status, at in events:
        key = str(job_id)
        if to_status == JobStatus.COMPLETED and key not in started:
            started[key] = at
        elif from_status == JobStatus.COMPLETED and key in started:
            out[key] += at - started.pop(key)
    for key, since in started.items():
        out[key] += max(now - since, timedelta(0))
    return out


def statuses(job_ids: list[Any]) -> dict[str, str]:
    return {str(i): s for i, s in Job.objects.filter(id__in=job_ids).values_list("id", "status")}
