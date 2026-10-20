"""A business's incident record for Fikisha staff (trust-and-disputes plan
A8). Plain reads; kept in four separate sections so an open report is
never read as a finding, a closure never as fault, and NO_FAULT never as an
unfounded report."""

from __future__ import annotations

from typing import Any

from fikisha.incidents.constants import FindingOutcome, FindingPartyKind, IncidentStatus, PartyKind
from fikisha.incidents.models import Incident, IncidentFinding, UnfoundedReport


def _incident_row(i: Incident) -> dict[str, Any]:
    return {
        "id": str(i.id),
        "job_id": str(i.job_id),
        "type": i.type,
        "reporter_party": i.reporter_party,
        "created_at": i.created_at.isoformat(),
    }


def business_record(business_id: Any) -> dict[str, Any]:
    on_jobs = Incident.objects.filter(job__business_id=business_id).select_related("closure")
    open_reports = [
        _incident_row(i)
        for i in on_jobs.exclude(status=IncidentStatus.RESOLVED).order_by("-created_at")
    ]
    closed = [
        {
            **_incident_row(i),
            "reason_code": getattr(getattr(i, "closure", None), "reason_code", None),
            "closed_at": i.closure.created_at.isoformat() if getattr(i, "closure", None) else None,
        }
        for i in on_jobs.filter(status=IncidentStatus.RESOLVED).order_by("-updated_at")[:50]
    ]
    findings = []
    for f in (
        IncidentFinding.objects.filter(
            outcome=FindingOutcome.AT_FAULT,
            parties__kind=FindingPartyKind.BUSINESS,
            parties__subject_id=business_id,
        )
        .select_related("incident")
        .order_by("-created_at")
    ):
        findings.append(
            {
                "id": str(f.id),
                "incident_id": str(f.incident_id),
                "job_id": str(f.incident.job_id),
                "type": f.incident.type,
                "reason": f.reason,
                "current": not hasattr(f, "superseded_by"),
                "created_at": f.created_at.isoformat(),
            }
        )
    unfounded = [
        {
            "incident_id": str(u.incident_id),
            "type": u.incident.type,
            "reason": u.reason,
            "created_at": u.created_at.isoformat(),
        }
        for u in UnfoundedReport.objects.filter(
            reporter_party=PartyKind.BUSINESS, incident__job__business_id=business_id
        )
        .select_related("incident")
        .order_by("-created_at")
    ]
    return {
        "open_reports": open_reports,
        "closed_incidents": closed,
        "findings_against": findings,
        "unfounded_reports": unfounded,
    }
