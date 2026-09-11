"""Read-side entry points into the Jobs module for sibling apps.

Sibling apps (``negotiation``, ``incidents``, …) read a Job through these
helpers rather than reaching for ``jobs.models`` directly, and **never** write
``job.status`` anywhere except via :func:`fikisha.jobs.service.transition`.
"""

from __future__ import annotations

from typing import Any

from django.http import Http404

from fikisha.jobs.models import Job, RecipientReportedIssue


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


def get_recipient_reported_issue(report_id: Any) -> RecipientReportedIssue:
    try:
        return RecipientReportedIssue.objects.select_related("job").get(id=report_id)
    except RecipientReportedIssue.DoesNotExist as exc:
        raise Http404("No such recipient report.") from exc


def current_config_version() -> Any:
    """The live ``PlatformConfigVersion`` row — an immutable snapshot (Step 9
    pins this onto every ``CommissionRecord``/``CommissionAdjustment`` so a
    historical financial row stays explainable after the config changes)."""
    from fikisha.platform_config.models import PlatformConfig

    cfg = PlatformConfig.objects.select_related("current_version").filter(pk=1).first()
    return cfg.current_version if cfg and cfg.current_version_id else None
