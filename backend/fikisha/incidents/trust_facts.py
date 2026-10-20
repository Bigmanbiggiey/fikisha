"""Incident facts for the operator tiers (``fikisha.trust``). Plain reads
over a set of jobs; the trust module's only view of incidents (module
boundary rule).

Counts incidents on the driver's jobs, not findings against the driver.
Never counted against the driver: a "Not paid" issue (the operator's own
complaint against the sender), and any incident the operator side reported
itself (trust-and-disputes plan A5). For incidents reported before the
reporter's side was stored, only the driver's own reports are recognised.
"""

from __future__ import annotations

from typing import Any

from django.db.models import Q

from fikisha.incidents.constants import (
    FindingOutcome,
    FindingPartyKind,
    IncidentStatus,
    IncidentType,
    PartyKind,
)
from fikisha.incidents.models import Incident, IncidentFindingParty

SERIOUS_TYPES = (
    IncidentType.LOSS,
    IncidentType.DAMAGE,
    IncidentType.MISSING_GOODS,
    IncidentType.MISCONDUCT,
)

_OPERATOR_SIDE = (PartyKind.OPERATOR, PartyKind.GROUP)


def incident_facts(job_ids: list[Any], *, driver_user_id: Any = None) -> dict[str, Any]:
    """``unresolved`` · ``serious_unresolved`` · ``unresolved_ids`` ·
    ``job_ids_with_incidents`` (any counted incident, resolved or not)."""
    own_reports = Q(reporter_party__in=_OPERATOR_SIDE)
    if driver_user_id is not None:
        own_reports |= Q(reporter_party="", reported_by_user_id=driver_user_id)
    qs = (
        Incident.objects.filter(job_id__in=job_ids)
        .exclude(type=IncidentType.NON_PAYMENT)
        .exclude(own_reports)
    )
    open_qs = qs.exclude(status=IncidentStatus.RESOLVED)
    return {
        "unresolved": open_qs.count(),
        "serious_unresolved": open_qs.filter(type__in=SERIOUS_TYPES).count(),
        "unresolved_ids": [str(i) for i in open_qs.values_list("id", flat=True)],
        "job_ids_with_incidents": {str(j) for j in qs.values_list("job_id", flat=True)},
    }


def finding_facts(driver_profile_id: Any, *, recent_job_ids: list[Any]) -> dict[str, Any]:
    """Current at-fault findings that name this driver (trust-and-disputes
    plan A5): ``at_fault_recent`` / ``at_fault_recent_ids`` (on the given
    recent jobs) and ``serious_at_fault`` / ``serious_at_fault_ids`` (on a
    serious incident type, any job). A finding naming the group never
    counts against the driver."""
    rows = list(
        IncidentFindingParty.objects.filter(
            kind=FindingPartyKind.DRIVER,
            subject_id=driver_profile_id,
            finding__outcome=FindingOutcome.AT_FAULT,
            finding__superseded_by__isnull=True,
        ).values_list("finding_id", "finding__incident__job_id", "finding__incident__type")
    )
    recent = {str(j) for j in recent_job_ids}
    recent_ids = [str(f) for f, job_id, _t in rows if str(job_id) in recent]
    serious_ids = [str(f) for f, _j, kind in rows if kind in SERIOUS_TYPES]
    return {
        "at_fault_recent": len(recent_ids),
        "at_fault_recent_ids": recent_ids,
        "serious_at_fault": len(serious_ids),
        "serious_at_fault_ids": serious_ids,
    }
