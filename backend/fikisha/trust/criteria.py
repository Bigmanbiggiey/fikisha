"""Progress toward the next tier (trust-architecture.md §1, operator-tiers
plan T-2). Deterministic and explainable: every criterion is a row with
its status, the operator's current figure and the target, and the whole
list is what a proposal snapshots.

Ratings and at-fault findings don't exist yet (TD-3): their rows are
``NOT_MEASURED`` and never block. Sources are the other modules' public
read surfaces (``jobs.driver_record``, ``incidents.trust_facts``,
``verification.services``).
"""

from __future__ import annotations

import copy
from datetime import datetime
from typing import Any

from django.utils import timezone

from fikisha.platform_config import services as config_service
from fikisha.platform_config.defaults import DEFAULT_CONFIG
from fikisha.trust.constants import NEXT_TIER, CriterionStatus, Tier

MET = CriterionStatus.MET
NOT_MET = CriterionStatus.NOT_MET
NOT_MEASURED = CriterionStatus.NOT_MEASURED


def tier_config() -> dict[str, Any]:
    """``trust_tiers`` config over the code defaults (a deployment seeded
    before tiers shipped has no such key)."""
    merged = copy.deepcopy(DEFAULT_CONFIG["trust_tiers"])
    stored = config_service.get("trust_tiers", default=None) or {}
    for key, value in stored.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key].update(value)
        else:
            merged[key] = value
    return merged


def _row(key: str, status: str, current: Any = None, target: Any = None) -> dict[str, Any]:
    return {"key": key, "status": str(status), "current": current, "target": target}


def _at_least(key: str, current: int, target: int) -> dict[str, Any]:
    return _row(key, MET if current >= target else NOT_MET, current, target)


def _none(key: str, count: int) -> dict[str, Any]:
    return _row(key, MET if count == 0 else NOT_MET, count, 0)


def floor_rows(profile: Any) -> list[dict[str, Any]]:
    """The verification floor: every mandatory operator domain verified and
    current (L1, and the floor under every tier)."""
    from fikisha.verification.models import State
    from fikisha.verification.requirements import required_domains_for_subject
    from fikisha.verification.services import eligibility

    states = eligibility(profile)
    return [
        _row(f"verified_{d.lower()}", MET if states.get(d) == State.VERIFIED else NOT_MET)
        for d in sorted(required_domains_for_subject(profile))
    ]


def floor_met(profile: Any) -> bool:
    return all(r["status"] == MET for r in floor_rows(profile))


def _days_since(moment: datetime | None) -> int:
    if moment is None:
        return 0
    return max(0, (timezone.now() - moment).days)


def facts(profile: Any) -> dict[str, Any]:
    from fikisha.incidents.trust_facts import incident_facts
    from fikisha.jobs.driver_record import driver_record
    from fikisha.verification.models import Domain
    from fikisha.verification.services import subject_meets

    cfg = tier_config()
    flag = cfg.get("late_cancellation_flag") or {}
    record = driver_record(
        profile.id, user_id=profile.user_id, late_window_days=int(flag.get("window_days", 30))
    )
    incidents = incident_facts(record["driven_job_ids"])
    with_incidents = incidents["job_ids_with_incidents"]
    clean_elevated = [j for j in record["elevated_completed_ids"] if j not in with_incidents]
    return {
        "completed_jobs": record["completed_jobs"],
        "days_active": _days_since(record["first_completed_at"]),
        "unresolved_incidents": incidents["unresolved"],
        "serious_unresolved_incidents": incidents["serious_unresolved"],
        "unresolved_incident_ids": incidents["unresolved_ids"],
        "clean_elevated_jobs": len(clean_elevated),
        "clean_elevated_job_ids": clean_elevated,
        "late_cancellations": record["late_cancellations"],
        "late_cancellation_limit": int(flag.get("count", 3)),
        "good_conduct": subject_meets(profile, [Domain.GOOD_CONDUCT]),
    }


def rows_for(target: str, f: dict[str, Any]) -> list[dict[str, Any]]:
    """The criteria for reaching ``target`` (L2 or L3) given the facts."""
    cfg = tier_config()
    need = cfg.get(target) or {}
    flagged = f["late_cancellations"] >= f["late_cancellation_limit"]
    rows = [
        _at_least("completed_jobs", f["completed_jobs"], int(need.get("min_completed_jobs", 0))),
        _at_least("days_active", f["days_active"], int(need.get("min_days_active", 0))),
        _row("avg_rating", NOT_MEASURED, None, need.get("min_avg_rating")),
    ]
    if target == Tier.L2:
        rows.append(_none("unresolved_incidents", f["unresolved_incidents"]))
    else:
        rows.append(_none("serious_unresolved_incidents", f["serious_unresolved_incidents"]))
        rows.append(
            _at_least(
                "clean_elevated_jobs",
                f["clean_elevated_jobs"],
                int(need.get("min_clean_elevated_jobs", 0)),
            )
        )
    rows += [
        _row("at_fault_findings", NOT_MEASURED),
        _row("good_conduct", MET if f["good_conduct"] else NOT_MET),
        _row(
            "no_cancellation_flag",
            NOT_MET if flagged else MET,
            f["late_cancellations"],
            f["late_cancellation_limit"],
        ),
    ]
    return rows


def progress(profile: Any, level: str) -> dict[str, Any]:
    """``{next_level, criteria, ready, facts}`` for an operator at ``level``.
    ``ready`` means every measured criterion for the next tier is met (only
    L2 / L3 are ever proposed; L1 is the verification floor itself)."""
    nxt = NEXT_TIER.get(level)  # type: ignore[call-overload]
    if nxt is None:
        return {"next_level": None, "criteria": [], "ready": False, "facts": None}
    if nxt == Tier.L1:
        rows = floor_rows(profile)
        return {"next_level": nxt, "criteria": rows, "ready": False, "facts": None}
    f = facts(profile)
    rows = rows_for(nxt, f)
    ready = all(r["status"] != NOT_MET for r in rows)
    return {"next_level": nxt, "criteria": rows, "ready": ready, "facts": f}
