"""Incident facts for the operator tiers (``fikisha.trust``, operator-tiers
plan T-2). Plain reads over a set of jobs; the trust module's only view of
incidents (module boundary rule).

No at-fault finding is recorded on an incident yet, so these are counts of
incidents on the driver's jobs, not findings against the driver. A
"Not paid" issue is the operator's own complaint against the sender and
never counts against them.
"""

from __future__ import annotations

from typing import Any

from fikisha.incidents.constants import IncidentStatus, IncidentType
from fikisha.incidents.models import Incident

SERIOUS_TYPES = (
    IncidentType.LOSS,
    IncidentType.DAMAGE,
    IncidentType.MISSING_GOODS,
    IncidentType.MISCONDUCT,
)


def incident_facts(job_ids: list[Any]) -> dict[str, Any]:
    """``unresolved`` · ``serious_unresolved`` · ``unresolved_ids`` ·
    ``job_ids_with_incidents`` (any incident, resolved or not)."""
    qs = Incident.objects.filter(job_id__in=job_ids).exclude(type=IncidentType.NON_PAYMENT)
    open_qs = qs.exclude(status=IncidentStatus.RESOLVED)
    return {
        "unresolved": open_qs.count(),
        "serious_unresolved": open_qs.filter(type__in=SERIOUS_TYPES).count(),
        "unresolved_ids": [str(i) for i in open_qs.values_list("id", flat=True)],
        "job_ids_with_incidents": {str(j) for j in qs.values_list("job_id", flat=True)},
    }
