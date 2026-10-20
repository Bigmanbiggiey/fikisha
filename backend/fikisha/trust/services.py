"""Operator tier services (trust-architecture.md §3, operator-tiers plan,
ADR-2D-52). The only writer of ``trust_level_state`` and
``trust_level_change``.

- **Effective tier** = the stored tier, but ``L0`` while the verification
  floor isn't met (a lapsed licence stops banded work whatever the tier).
- **Proposals**: ``evaluate`` writes a ``PROPOSED`` change when every
  measured criterion for the next tier is met. Nothing advances on its own.
- **Platform Admin levers** (TD-1): confirm or reject a proposal, or change
  the tier directly (``ADMIN_OVERRIDE``, shown as manual). Each needs a
  reason and a fresh step-up, writes an append-only change and an audit row
  in one transaction, and can't target the admin's own operator profile.

A demotion affects new assignments only; jobs already assigned keep their
driver (staff can reassign).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound

from fikisha.audit import services as audit
from fikisha.common.exceptions import AuthorizationError, DomainError
from fikisha.identity.authz.policies import actor_has_permission
from fikisha.identity.authz.step_up import require_step_up
from fikisha.outbox.services import emit
from fikisha.platform_config import services as config_service
from fikisha.trust import criteria
from fikisha.trust.constants import (
    STORED_TIERS,
    TIER_ORDER,
    ChangeStatus,
    ChangeTrigger,
    ProposedBy,
    Tier,
)
from fikisha.trust.models import TrustLevelChange, TrustLevelState

MANAGE_PERMISSION = "trust.change.apply"
REASON_MIN_LENGTH = 10


class InvalidTierChange(DomainError):
    default_code = "invalid_tier_change"


class TierChangeNotAllowed(DomainError):
    status_code = status.HTTP_409_CONFLICT
    default_code = "tier_change_not_allowed"


class ProposalNotOpen(DomainError):
    status_code = status.HTTP_409_CONFLICT
    default_code = "tier_proposal_not_open"


# ─── Reads ──────────────────────────────────────────────────────────────
def stored_level(operator_id: Any) -> str:
    level = TrustLevelState.objects.filter(operator_id=operator_id).values_list("level", flat=True)
    return str(level.first() or Tier.L1)


def effective_level(profile: Any) -> str:
    """``L0`` / ``L1`` / ``L2`` / ``L3`` / ``RESTRICTED``."""
    if not criteria.floor_met(profile):
        return Tier.L0
    return stored_level(profile.id)


def covers(level: str, need: str) -> bool:
    """Does ``level`` reach a band whose configured minimum is ``need``?"""
    return TIER_ORDER.get(level, 0) >= TIER_ORDER.get(need, 99) and level != Tier.L0  # type: ignore[call-overload]


def bands_for(level: str) -> dict[str, Any]:
    """The value bands ``level`` may take, and the highest declared value
    (KES minor units; ``None`` = no cap, VERY_HIGH still needs per-job
    Platform-Admin approval)."""
    bands: list[str] = []
    cap: int | None = 0
    for entry in config_service.get("value_bands", default=[]) or []:
        if covers(level, str(entry.get("min_trust_level", "L1"))):
            bands.append(str(entry["band"]))
            cap = entry.get("max_declared_value_kes")
    return {"bands": bands, "max_value_kes": cap if bands else 0}


def _open_proposal(operator_id: Any, current: str) -> TrustLevelChange | None:
    """The undecided proposal made from the operator's current tier (one made
    from an earlier tier went stale when the tier changed)."""
    return (
        TrustLevelChange.objects.filter(
            operator_id=operator_id,
            status=ChangeStatus.PROPOSED,
            from_level=current,
            decisions__isnull=True,
        )
        .order_by("-created_at")
        .first()
    )


def _change_view(change: TrustLevelChange, *, staff: bool) -> dict[str, Any]:
    out = {
        "id": str(change.id),
        "from_level": change.from_level,
        "to_level": change.to_level,
        "trigger": change.trigger,
        "status": change.status,
        "reason": change.reason,
        "created_at": change.created_at.isoformat(),
    }
    if staff:
        user = change.actor
        out["by"] = (
            (getattr(user, "display_name", "") or getattr(user, "phone", "")) if user else ""
        )
    return out


def history(operator_id: Any, *, staff: bool, limit: int = 50) -> list[dict[str, Any]]:
    rows = (
        TrustLevelChange.objects.filter(operator_id=operator_id)
        .exclude(status=ChangeStatus.PROPOSED)
        .select_related("actor")
        .order_by("-created_at")[:limit]
    )
    return [_change_view(c, staff=staff) for c in rows]


def tier_view(profile: Any, *, staff: bool = False) -> dict[str, Any]:
    """Everything the tier card shows: the tier and what it allows, the
    checklist toward the next tier, the open proposal and the history."""
    stored = stored_level(profile.id)
    floor = criteria.floor_met(profile)
    level = stored if floor else Tier.L0
    state = TrustLevelState.objects.filter(operator_id=profile.id).first()
    prog = criteria.progress(profile, level)
    proposal = _open_proposal(profile.id, stored) if floor else None
    return {
        "operator_id": str(profile.id),
        "operator_name": profile.display_name or profile.full_name,
        "level": level,
        "stored_level": stored,
        "floor_met": floor,
        "since": state.since.isoformat() if state and state.since else None,
        **bands_for(level),
        "next_level": prog["next_level"],
        "criteria": prog["criteria"],
        "ready_for_review": prog["ready"],
        "open_proposal": _change_view(proposal, staff=staff) if proposal else None,
        "history": history(profile.id, staff=staff),
    }


def open_proposals(limit: int = 100) -> list[dict[str, Any]]:
    """Every undecided, still-current proposal — the staff queue."""
    from fikisha.operators import services as operators

    out: list[dict[str, Any]] = []
    rows = TrustLevelChange.objects.filter(
        status=ChangeStatus.PROPOSED, decisions__isnull=True
    ).order_by("created_at")[: limit * 2]
    for change in rows:
        if stored_level(change.operator_id) != change.from_level:
            continue
        out.append(
            {
                **_change_view(change, staff=True),
                "operator_id": str(change.operator_id),
                "operator_name": operators.display_name_for(change.operator_id) or "",
            }
        )
        if len(out) >= limit:
            break
    return out


# ─── Writes ─────────────────────────────────────────────────────────────
def _locked_state(operator_id: Any) -> TrustLevelState:
    try:
        with transaction.atomic():
            state, _ = TrustLevelState.objects.select_for_update().get_or_create(
                operator_id=operator_id, defaults={"level": Tier.L1}
            )
    except IntegrityError:  # created concurrently: it exists now
        state = TrustLevelState.objects.select_for_update().get(operator_id=operator_id)
    return state


def _snapshot(profile: Any, level: str) -> tuple[dict[str, Any], list[str], list[str]]:
    prog = criteria.progress(profile, level)
    f = prog["facts"] or {}
    snapshot = {
        "level": level,
        "next_level": prog["next_level"],
        "criteria": prog["criteria"],
        "evaluated_at": timezone.now().isoformat(),
    }
    return (
        snapshot,
        list(f.get("clean_elevated_job_ids") or []),
        list(f.get("unresolved_incident_ids") or []),
    )


def evaluate(profile: Any) -> TrustLevelChange | None:
    """Propose the next tier when every measured criterion is met and no
    proposal for it is open; a rejected proposal isn't re-made for
    ``reproposal_cooldown_days``. Never applies anything."""
    with transaction.atomic():
        state = _locked_state(profile.id)
        state.last_evaluated_at = timezone.now()
        state.save(update_fields=["last_evaluated_at", "updated_at"])
        current = state.level
        if current not in (Tier.L1, Tier.L2) or not criteria.floor_met(profile):
            return None
        prog = criteria.progress(profile, current)
        target = prog["next_level"]
        if not prog["ready"] or target is None:
            return None
        if _open_proposal(profile.id, current) is not None:
            return None
        cooldown = int(criteria.tier_config().get("reproposal_cooldown_days", 30))
        recently_rejected = TrustLevelChange.objects.filter(
            operator_id=profile.id,
            trigger=ChangeTrigger.ADMIN_REJECTED,
            from_level=current,
            to_level=target,
            created_at__gte=timezone.now() - timedelta(days=cooldown),
        ).exists()
        if recently_rejected:
            return None
        snapshot, job_ids, incident_ids = _snapshot(profile, current)
        change = TrustLevelChange.objects.create(
            operator_id=profile.id,
            from_level=current,
            to_level=target,
            trigger=ChangeTrigger.AUTO_PROPOSED,
            status=ChangeStatus.PROPOSED,
            reason="Every measured criterion for the next tier is met.",
            proposed_by=ProposedBy.SYSTEM,
            criteria_snapshot=snapshot,
            evidence_job_ids=job_ids,
            evidence_incident_ids=incident_ids,
            config_version=config_service.current_version(),
        )
        audit.record(
            actor=None,
            action="trust.change.proposed",
            entity_type="operator",
            entity_id=profile.id,
            before={"level": current},
            after={"proposed_level": target, "change_id": str(change.id)},
            source_channel="SCHEDULER",
        )
    return change


def evaluate_operator_id(operator_id: Any) -> TrustLevelChange | None:
    from fikisha.operators import services as operators

    profile = operators.profile_by_id(operator_id)
    return evaluate(profile) if profile is not None else None


def _require_manager(actor: Any, profile: Any, reason: str) -> str:
    if not actor_has_permission(actor, MANAGE_PERMISSION):
        raise AuthorizationError(f"missing permission {MANAGE_PERMISSION!r}")
    reason = (reason or "").strip()
    if len(reason) < REASON_MIN_LENGTH:
        raise InvalidTierChange(f"Give a reason of at least {REASON_MIN_LENGTH} characters.")
    if str(profile.user_id) == str(getattr(getattr(actor, "user", None), "id", "")):
        raise TierChangeNotAllowed("You can't change the tier of your own operator profile.")
    require_step_up(actor)
    return reason


def _apply(
    *,
    actor: Any,
    profile: Any,
    state: TrustLevelState,
    to_level: str,
    trigger: str,
    reason: str,
    decides: TrustLevelChange | None,
    audit_action: str,
) -> TrustLevelChange:
    before = state.level
    snapshot, job_ids, incident_ids = _snapshot(profile, before)
    version = config_service.current_version()
    change = TrustLevelChange.objects.create(
        operator_id=profile.id,
        from_level=before,
        to_level=to_level,
        trigger=trigger,
        status=ChangeStatus.APPLIED,
        reason=reason,
        proposed_by=ProposedBy.ADMIN,
        actor=getattr(actor, "user", None),
        decides=decides,
        criteria_snapshot=snapshot,
        evidence_job_ids=job_ids,
        evidence_incident_ids=incident_ids,
        config_version=version,
    )
    state.level = to_level
    state.since = timezone.now()
    state.config_version = version
    state.save(update_fields=["level", "since", "config_version", "updated_at"])
    audit.record(
        actor=actor,
        action=audit_action,
        entity_type="operator",
        entity_id=profile.id,
        before={"level": before},
        after={"level": to_level, "reason": reason, "change_id": str(change.id)},
        source_channel="ADMIN_UI",
    )
    emit(
        event_type="TrustLevelChanged",
        aggregate_type="operator",
        aggregate_id=str(profile.id),
        payload={"from_level": before, "to_level": to_level, "trigger": trigger},
    )
    return change


def _profile(operator_id: Any) -> Any:
    from fikisha.operators import services as operators

    profile = operators.profile_by_id(operator_id)
    if profile is None:
        raise NotFound("No such operator.")
    return profile


def set_level(*, actor: Any, operator_id: Any, level: str, reason: str) -> TrustLevelChange:
    """A Platform Admin's direct promote / demote (TD-1, recorded as manual)."""
    profile = _profile(operator_id)
    reason = _require_manager(actor, profile, reason)
    if level not in STORED_TIERS:
        raise InvalidTierChange(f"Unknown tier {level!r}.")
    with transaction.atomic():
        state = _locked_state(profile.id)
        if state.level == level:
            raise TierChangeNotAllowed(f"This operator is already {level}.")
        return _apply(
            actor=actor,
            profile=profile,
            state=state,
            to_level=level,
            trigger=ChangeTrigger.ADMIN_OVERRIDE,
            reason=reason,
            decides=None,
            audit_action="trust.change.manual",
        )


def decide_proposal(*, actor: Any, change_id: Any, confirm: bool, reason: str) -> TrustLevelChange:
    """Confirm (apply) or reject a system proposal."""
    proposal = TrustLevelChange.objects.filter(id=change_id, status=ChangeStatus.PROPOSED).first()
    if proposal is None:
        raise NotFound("No such proposal.")
    profile = _profile(proposal.operator_id)
    reason = _require_manager(actor, profile, reason)
    with transaction.atomic():
        state = _locked_state(profile.id)
        if proposal.decisions.exists() or state.level != proposal.from_level:
            raise ProposalNotOpen("This proposal has already been decided or is out of date.")
        if confirm:
            if not criteria.floor_met(profile):
                raise TierChangeNotAllowed(
                    "The operator's verification isn't current; renew it before promoting."
                )
            return _apply(
                actor=actor,
                profile=profile,
                state=state,
                to_level=proposal.to_level,
                trigger=ChangeTrigger.ADMIN_CONFIRMED,
                reason=reason,
                decides=proposal,
                audit_action="trust.change.confirmed",
            )
        change = TrustLevelChange.objects.create(
            operator_id=profile.id,
            from_level=state.level,
            to_level=proposal.to_level,
            trigger=ChangeTrigger.ADMIN_REJECTED,
            status=ChangeStatus.REJECTED,
            reason=reason,
            proposed_by=ProposedBy.ADMIN,
            actor=getattr(actor, "user", None),
            decides=proposal,
            config_version=config_service.current_version(),
        )
        audit.record(
            actor=actor,
            action="trust.change.rejected",
            entity_type="operator",
            entity_id=profile.id,
            before={"level": state.level},
            after={
                "rejected_level": proposal.to_level,
                "reason": reason,
                "change_id": str(change.id),
            },
            source_channel="ADMIN_UI",
        )
        return change
