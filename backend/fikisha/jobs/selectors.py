"""Read-side entry points into the Jobs module for sibling apps.

Sibling apps (``negotiation``, ``incidents``, …) read a Job through these
helpers rather than reaching for ``jobs.models`` directly, and **never** write
``job.status`` anywhere except via :func:`fikisha.jobs.service.transition`.
"""

from __future__ import annotations

from typing import Any

from django.http import Http404

from fikisha.jobs.models import Job


def get_job(job_id: Any) -> Job:
    try:
        return Job.objects.select_related("business", "config_version").get(id=job_id)
    except Job.DoesNotExist as exc:
        raise Http404("No such job.") from exc


def job_for_update(job_id: Any) -> Job:
    """Row-locked load — call only inside an open transaction."""
    try:
        return Job.objects.select_for_update().get(id=job_id)
    except Job.DoesNotExist as exc:
        raise Http404("No such job.") from exc
