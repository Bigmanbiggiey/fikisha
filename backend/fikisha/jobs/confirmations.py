"""Which pickup / delivery confirmations still count (trust-and-disputes plan
B2, DR-7).

After a disputed job is resumed, confirmations made before the resume no
longer count: the pending step is confirmed again, because the goods may
have changed while the job was frozen. The old rows stay in the append-only
table (shown as history); they are only left out of what counts. Before any
resume this is every confirmation for the job.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from django.db.models import QuerySet

from fikisha.jobs.constants import JobEventType
from fikisha.jobs.models import CustodyConfirmation, JobEvent


def last_resumed_at(job: Any) -> datetime | None:
    return (
        JobEvent.objects.filter(job_id=job.id, type=JobEventType.RESUMED)
        .order_by("-server_time")
        .values_list("server_time", flat=True)
        .first()
    )


def counted(job: Any, stage: str | None = None) -> QuerySet[CustodyConfirmation]:
    qs = CustodyConfirmation.objects.filter(job_id=job.id)
    if stage is not None:
        qs = qs.filter(stage=stage)
    since = last_resumed_at(job)
    if since is not None:
        qs = qs.filter(created_at__gt=since)
    return qs
