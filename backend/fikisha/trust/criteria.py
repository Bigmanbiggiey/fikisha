"""Progress toward the next tier (trust-architecture.md §1, operator-tiers
plan T-2). Deterministic and explainable: every criterion is a row with
its status, the operator's current figure and the target, and the whole
list is what a proposal snapshots.

Ratings and at-fault findings count only once ``live_criteria`` is on
(trust-and-disputes plan A5); until then, like operator cancellations /
no-shows (never recorded, CF-1), their rows are ``NOT_MEASURED`` and never
block (TD-3). Live, fewer than 3 counted ratings is ``INSUFFICIENT_DATA``,
which blocks (TE-11). Sources are the other modules' public
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
INSUFFICIENT_DATA = CriterionStatus.INSUFFICIENT_DATA

#: Statuses that stop a proposal. NOT_MEASURED never does (TD-3).
BLOCKING = (NOT_MET, INSUFFICIENT_DATA)


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


def live() -> bool:
    return bool(tier_config().get("live_criteria"))


def _rating_facts(profile: Any) -> dict[str, Any]:
    """The driver's rating average and how concentrated the ratings behind
    it are (T-5: information for the confirming admin, never a block)."""
    from fikisha.ratings import services as ratings

    avg = ratings.average("DRIVER", profile.id)
    by_business = ratings.businesses_of(avg["rating_ids"])
    top = max(by_business.values(), default=0)
    return {
        "rating_average": avg["average"],
        "rating_count": avg["count"],
        "rating_enough": avg["enough"],
        "rating_ids": avg["rating_ids"],
        "rating_concentration": {"top": top, "of": avg["count"]},
    }


def facts(profile: Any) -> dict[str, Any]:
    from fikisha.incidents.trust_facts import finding_facts, incident_facts
    from fikisha.jobs.driver_record import driver_record, recent_driven_job_ids
    from fikisha.verification.models import Domain
    from fikisha.verification.services import subject_meets

    cfg = tier_config()
    window = int((cfg.get("L2") or {}).get("at_fault_window_jobs", 20))
    findings = finding_facts(
        profile.id, recent_job_ids=recent_driven_job_ids(profile.id, limit=window)
    )
    record = driver_record(profile.id)
    incidents = incident_facts(record["driven_job_ids"], driver_user_id=profile.user_id)
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
        "good_conduct": subject_meets(profile, [Domain.GOOD_CONDUCT]),
        **findings,
        **_rating_facts(profile),
    }


def _rating_row(target: str, f: dict[str, Any], need: dict[str, Any]) -> dict[str, Any]:
    goal = need.get("min_avg_rating")
    if not live():
        return _row("avg_rating", NOT_MEASURED, None, goal)
    if not f["rating_enough"]:
        return _row("avg_rating", INSUFFICIENT_DATA, f["rating_count"], goal)
    return _row(
        "avg_rating",
        MET if f["rating_average"] >= float(goal or 0) else NOT_MET,
        f["rating_average"],
        goal,
    )


def _fault_row(target: str, f: dict[str, Any], need: dict[str, Any]) -> dict[str, Any]:
    if target == Tier.L2:
        limit = int(need.get("max_at_fault_findings", 1))
        if not live():
            return _row("at_fault_findings", NOT_MEASURED, None, limit)
        count = f["at_fault_recent"]
        return _row("at_fault_findings", MET if count <= limit else NOT_MET, count, limit)
    if not live():
        return _row("serious_at_fault_findings", NOT_MEASURED, None, 0)
    return _none("serious_at_fault_findings", f["serious_at_fault"])


def rows_for(target: str, f: dict[str, Any]) -> list[dict[str, Any]]:
    """The criteria for reaching ``target`` (L2 or L3) given the facts."""
    cfg = tier_config()
    need = cfg.get(target) or {}
    rows = [
        _at_least("completed_jobs", f["completed_jobs"], int(need.get("min_completed_jobs", 0))),
        _at_least("days_active", f["days_active"], int(need.get("min_days_active", 0))),
        _rating_row(target, f, need),
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
        _fault_row(target, f, need),
        _row("good_conduct", MET if f["good_conduct"] else NOT_MET),
        # Operators can't cancel and no-shows aren't recorded (CF-1).
        _row("no_cancellation_flag", NOT_MEASURED),
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
    ready = all(r["status"] not in BLOCKING for r in rows)
    return {"next_level": nxt, "criteria": rows, "ready": ready, "facts": f}
