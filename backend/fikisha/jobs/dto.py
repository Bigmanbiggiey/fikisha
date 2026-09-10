"""``JobView`` — the read projection returned by ``JobLifecycleService.transition``
and by the job read endpoints (later increment).

It is a plain JSON-serialisable ``dict`` (not a model) so it can be stored
verbatim in the idempotency row and replayed byte-for-byte (job-state-machine.md
§2.1 step 12).
"""

from __future__ import annotations

from typing import Any

from fikisha.jobs.constants import TERMINAL_STATES
from fikisha.jobs.transitions import ALLOWED_TRANSITIONS


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def next_allowed_statuses(status: str) -> list[str]:
    """The ``to`` states reachable from ``status`` via the authoritative table.

    This is the *structural* set — it does not evaluate guards or the actor.
    """
    return sorted({to for (frm, to) in ALLOWED_TRANSITIONS if frm == status})


def job_view(job: Any) -> dict[str, Any]:
    """Serialise a ``Job`` aggregate to the canonical view dict."""
    return {
        "id": str(job.id),
        "status": job.status,
        "version": job.version,
        "business_id": str(job.business_id),
        "created_by_id": str(job.created_by_id),
        "value_band": job.value_band,
        "required_trust_level": job.required_trust_level,
        "is_high_value": job.is_high_value,
        "latent_risk_cargo": job.latent_risk_cargo,
        "declared_value_kes": job.declared_value_kes,
        "proposed_price_kes": job.proposed_price_kes,
        "agreement_id": str(job.agreement_id) if job.agreement_id else None,
        "assignment_id": str(job.assignment_id) if job.assignment_id else None,
        "config_version_id": str(job.config_version_id) if job.config_version_id else None,
        "is_terminal": job.status in TERMINAL_STATES,
        "next_allowed_statuses": next_allowed_statuses(job.status),
        "timestamps": {
            "created_at": _iso(job.created_at),
            "published_at": _iso(job.published_at),
            "confirmed_at": _iso(job.confirmed_at),
            "assigned_at": _iso(job.assigned_at),
            "picked_up_at": _iso(job.picked_up_at),
            "delivered_at": _iso(job.delivered_at),
            "completed_at": _iso(job.completed_at),
            "terminal_at": _iso(job.terminal_at),
        },
    }
