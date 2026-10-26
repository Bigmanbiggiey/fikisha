"""Late-cancellation review flags for businesses (D-DIS-3, trust-and-disputes
plan A7). A review item for staff, never an automatic penalty.

A business is flagged when it has at least ``count`` late cancellations or
wasted trips (cancelled at ASSIGNED, or at AT_PICKUP or later) in the last
``window_days``. Only cancellations by the business count: staff
cancellations count against no one (CF-2), and operators can't cancel
(CF-1). Rows written before the cancelling side was stored are attributed
from the role recorded at the time — USER is the business (the only
non-staff path since the cancel API was added), staff roles are staff —
never from anyone's current memberships.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from fikisha.audit import services as audit
from fikisha.common.exceptions import AuthorizationError, ConflictError, DomainError
from fikisha.identity.authz.policies import actor_has_permission
from fikisha.jobs.constants import CancellationFlagStatus, CancellingSide, PenaltyClass
from fikisha.jobs.models import CancellationFlag, CancellationFlagReview, CancellationRecord
from fikisha.outbox.services import emit
from fikisha.platform_config import services as config_service

NOTE_MIN_LENGTH = 10

_BY_BUSINESS = Q(cancelling_side=CancellingSide.BUSINESS) | Q(
    cancelling_side="", cancelled_by_role="USER"
)


class FlagNotOpen(ConflictError):
    default_code = "cancellation_flag_not_open"
    default_detail = "This flag has already been reviewed."


class FlagNoteRequired(DomainError):
    default_code = "flag_note_required"
    status_code = 422
    default_detail = "Add a note of at least 10 characters."


def _rule() -> tuple[int, int]:
    cfg = config_service.get("trust_tiers.late_cancellation_flag", default=None) or {}
    return int(cfg.get("count", 3)), int(cfg.get("window_days", 30))


def qualifying_records(business_id: Any, *, now: Any = None) -> QuerySet[CancellationRecord]:
    """The business's late cancellations / wasted trips inside the window."""
    _count, days = _rule()
    since = (now or timezone.now()) - timedelta(days=days)
    return (
        CancellationRecord.objects.filter(job__business_id=business_id, created_at__gte=since)
        .exclude(penalty_class=PenaltyClass.NONE)
        .filter(_BY_BUSINESS)
        .order_by("created_at")
    )


def check_business(business_id: Any) -> CancellationFlag | None:
    """Open a flag when the business reaches the threshold and has none
    open. Runs inside the cancellation's transaction."""
    threshold, _days = _rule()
    records = list(qualifying_records(business_id))
    if len(records) < threshold:
        return None
    if CancellationFlag.objects.filter(
        business_id=business_id, status=CancellationFlagStatus.OPEN
    ).exists():
        return None
    try:
        with transaction.atomic():
            flag = CancellationFlag.objects.create(
                business_id=business_id, record_ids=[str(r.id) for r in records]
            )
    except IntegrityError:  # opened concurrently
        return None
    audit.record(
        actor=None,
        action="cancellation_flag.opened",
        entity_type="business",
        entity_id=business_id,
        after={"flag_id": str(flag.id), "records": len(records)},
        source_channel="SYSTEM",
    )
    emit(
        event_type="CancellationFlagOpened",
        aggregate_type="business",
        aggregate_id=str(business_id),
        payload={"flag_id": str(flag.id), "records": len(records)},
    )
    return flag


def open_flags(limit: int = 100) -> list[dict[str, Any]]:
    from fikisha.business import services as business

    flags = list(
        CancellationFlag.objects.filter(status=CancellationFlagStatus.OPEN).order_by("created_at")[
            :limit
        ]
    )
    names = business.display_names_for([f.business_id for f in flags])
    return [
        {
            "id": str(f.id),
            "business_id": str(f.business_id),
            "business_name": names.get(str(f.business_id), ""),
            "count": len(f.record_ids),
            "created_at": f.created_at.isoformat(),
        }
        for f in flags
    ]


def flags_for_business(business_id: Any) -> list[dict[str, Any]]:
    """Every flag for one business, newest first, with its review."""
    rows = CancellationFlag.objects.filter(business_id=business_id).order_by("-created_at")
    out = []
    for f in rows:
        review = getattr(f, "review", None)
        out.append(
            {
                "id": str(f.id),
                "status": f.status,
                "count": len(f.record_ids),
                "created_at": f.created_at.isoformat(),
                "review": {"outcome": review.outcome, "note": review.note}
                if review is not None
                else None,
            }
        )
    return out


@transaction.atomic
def review_flag(*, actor: Any, flag_id: Any, mistaken: bool, note: str) -> CancellationFlag:
    """Staff clear a flag with a note, or close it as mistaken."""
    if not actor_has_permission(actor, "job.intervene"):
        raise AuthorizationError("Reviewing a cancellation flag requires staff.")
    note = (note or "").strip()
    if len(note) < NOTE_MIN_LENGTH:
        raise FlagNoteRequired()
    flag = CancellationFlag.objects.select_for_update().filter(id=flag_id).first()
    if flag is None:
        from rest_framework.exceptions import NotFound

        raise NotFound("No such flag.")
    if flag.status != CancellationFlagStatus.OPEN:
        raise FlagNotOpen()
    outcome = CancellationFlagStatus.MISTAKEN if mistaken else CancellationFlagStatus.CLEARED
    user: Any = getattr(actor, "user", None)
    CancellationFlagReview.objects.create(flag=flag, outcome=outcome, note=note, reviewed_by=user)
    flag.status = outcome
    flag.save(update_fields=["status", "updated_at"])
    audit.record(
        actor=actor,
        action="cancellation_flag.reviewed",
        entity_type="business",
        entity_id=flag.business_id,
        after={"flag_id": str(flag.id), "outcome": outcome},
    )
    return flag
