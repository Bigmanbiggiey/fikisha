"""Ratings (trust-and-disputes plan A4; decisions TE-1..TE-4, TE-8..TE-11).

- **Window (TE-1):** each side may rate while the job is COMPLETED, it
  hasn't rated yet, and the job has spent less than ``window_days`` in
  COMPLETED in total. Time DISPUTED doesn't count; a job that ends FAILED or
  CANCELLED can't be rated further.
- **Published (TE-2):** both sides have rated, or the job has spent the
  whole window in COMPLETED. Both only ever become true, so a published
  rating stays published, and nothing is newly published during a dispute.
  Computed on read from the stored rows and ``now``: no sweep, no flag.
- **Counted:** published, and the job is COMPLETED now.
- **Visibility (TE-3, TE-8):** staff see everything; the rated side sees
  published scores only, never the comment; the rater sees their own.
"""

from __future__ import annotations

import copy
from datetime import datetime, timedelta
from typing import Any

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status

from fikisha.audit import services as audit
from fikisha.common.exceptions import AuthorizationError, ConflictError, DomainError
from fikisha.incidents import authz as incidents_authz
from fikisha.jobs import job_authz
from fikisha.jobs import rating_facts as job_facts
from fikisha.jobs.constants import JobStatus
from fikisha.jobs.selectors import job_for_update
from fikisha.outbox.services import emit
from fikisha.platform_config import services as config_service
from fikisha.platform_config.defaults import DEFAULT_CONFIG
from fikisha.ratings.constants import (
    COMMENT_MAX_LENGTH,
    MAX_SCORE,
    MIN_SCORE,
    RaterParty,
    RatingSide,
    SubjectKind,
)
from fikisha.ratings.models import Rating


class NotRatingParty(AuthorizationError):
    default_code = "not_rating_party"
    default_detail = "Only the job's business or operator side can rate it."


class RatingNotOpen(ConflictError):
    default_code = "rating_not_open"
    default_detail = "This job can't be rated now."


class AlreadyRated(ConflictError):
    default_code = "already_rated"
    default_detail = "Your side has already rated this job."


class InvalidRating(DomainError):
    default_code = "invalid_rating"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "Give a score from 1 to 5; a comment can be up to 1,000 characters."


def rating_config() -> dict[str, Any]:
    merged = copy.deepcopy(DEFAULT_CONFIG["ratings"])
    merged.update(config_service.get("ratings", default=None) or {})
    return merged


def _window() -> timedelta:
    return timedelta(days=float(rating_config()["window_days"]))


def _actor_user(actor: Any) -> Any:
    user = getattr(actor, "user", actor)
    return user if getattr(user, "pk", None) else None


def side_for(actor: Any, job: Any) -> tuple[str, str] | None:
    """``(side, rater_party)`` the actor rates for, or ``None``. Staff never
    rate; a business party rates the operator side; the solo operator, the
    assigned driver or the group manager rates the business."""
    if job_authz.is_admin(actor):
        return None
    if job_authz.business_is_party(actor, job):
        return RatingSide.BUSINESS_RATES_OPERATOR, RaterParty.BUSINESS
    if not incidents_authz.operator_is_party(actor, job):
        return None
    if incidents_authz.is_group_party(actor, job):
        return RatingSide.OPERATOR_RATES_BUSINESS, RaterParty.GROUP
    assignment = getattr(job, "assignment", None)
    user = _actor_user(actor)
    driver = getattr(assignment, "assigned_driver_profile", None)
    if assignment is not None and assignment.group_id is not None:
        if driver is not None and user is not None and driver.user_id == user.id:
            return RatingSide.OPERATOR_RATES_BUSINESS, RaterParty.DRIVER
    return RatingSide.OPERATOR_RATES_BUSINESS, RaterParty.OPERATOR


@transaction.atomic
def submit(
    *, actor: Any, job_id: Any, score: int, comment: str = "", now: datetime | None = None
) -> Rating:
    now = now or timezone.now()
    if not isinstance(score, int) or not MIN_SCORE <= score <= MAX_SCORE:
        raise InvalidRating()
    comment = (comment or "").strip()
    if len(comment) > COMMENT_MAX_LENGTH:
        raise InvalidRating()
    job = job_for_update(job_id)
    side = side_for(actor, job)
    if side is None:
        raise NotRatingParty()
    side_code, rater_party = side
    if job.status != JobStatus.COMPLETED:
        raise RatingNotOpen("Only a completed job can be rated.")
    if job_facts.time_in_completed([job.id], now=now)[str(job.id)] >= _window():
        raise RatingNotOpen("The time to rate this job has passed.")
    if Rating.objects.filter(job=job, side=side_code).exists():
        raise AlreadyRated()
    subjects = job_facts.rating_subjects(job)
    fields: dict[str, Any] = {}
    if side_code == RatingSide.BUSINESS_RATES_OPERATOR:
        fields = {
            "driver_profile_id": subjects["driver_profile_id"],
            "group_id": subjects["group_id"],
        }
    else:
        fields = {"business_id": subjects["business_id"]}
    try:
        with transaction.atomic():
            rating = Rating.objects.create(
                job=job,
                side=side_code,
                score=score,
                comment=comment,
                rater=_actor_user(actor),
                rater_party=rater_party,
                **fields,
            )
    except IntegrityError as exc:  # the other device of the same side won
        raise AlreadyRated() from exc
    audit.record(
        actor=actor,
        action="rating.submitted",
        entity_type="job",
        entity_id=job.id,
        after={"rating_id": str(rating.id), "side": side_code, "score": score},
    )
    emit(
        event_type="RatingSubmitted",
        aggregate_type="job",
        aggregate_id=str(job.id),
        payload={
            "job_id": str(job.id),
            "rating_id": str(rating.id),
            "side": side_code,
            "driver_profile_id": str(fields.get("driver_profile_id") or "") or None,
        },
    )
    return rating


# ─── publication and counting ─────────────────────────────────────────
def _states(ratings: list[Rating], *, now: datetime) -> dict[str, dict[str, bool]]:
    """``{rating_id: {published, counted}}``."""
    job_ids = list({r.job_id for r in ratings})
    if not job_ids:
        return {}
    in_completed = job_facts.time_in_completed(job_ids, now=now)
    statuses = job_facts.statuses(job_ids)
    sides: dict[str, set[str]] = {}
    for job_id, side in Rating.objects.filter(job_id__in=job_ids).values_list("job_id", "side"):
        sides.setdefault(str(job_id), set()).add(side)
    window = _window()
    out: dict[str, dict[str, bool]] = {}
    for r in ratings:
        key = str(r.job_id)
        published = len(sides.get(key, ())) == 2 or in_completed.get(key, timedelta(0)) >= window
        out[str(r.id)] = {
            "published": published,
            "counted": published and statuses.get(key) == JobStatus.COMPLETED,
        }
    return out


def counted(kind: str, subject_id: Any, *, now: datetime | None = None) -> list[Rating]:
    """Counted ratings about one subject (DRIVER, GROUP or BUSINESS), newest
    first (submission time, then id)."""
    now = now or timezone.now()
    field = {
        SubjectKind.DRIVER: "driver_profile_id",
        SubjectKind.GROUP: "group_id",
        SubjectKind.BUSINESS: "business_id",
    }[kind]  # type: ignore[index]
    rows = list(Rating.objects.filter(**{field: subject_id}).order_by("-created_at", "-id"))
    states = _states(rows, now=now)
    return [r for r in rows if states[str(r.id)]["counted"]]


def average(kind: str, subject_id: Any, *, now: datetime | None = None) -> dict[str, Any]:
    """``{count, average, rating_ids, enough}`` over the newest ``average_of``
    counted ratings; ``enough`` is False below ``min_counted`` (TE-4) and the
    average is then ``None``."""
    cfg = rating_config()
    rows = counted(kind, subject_id, now=now)[: int(cfg["average_of"])]
    enough = len(rows) >= int(cfg["min_counted"])
    return {
        "count": len(rows),
        "average": round(sum(r.score for r in rows) / len(rows), 2) if enough else None,
        "rating_ids": [str(r.id) for r in rows],
        "enough": enough,
    }


def _rating_view(r: Rating, state: dict[str, bool], *, comment: bool) -> dict[str, Any]:
    view: dict[str, Any] = {
        "id": str(r.id),
        "side": r.side,
        "score": r.score,
        "published": state["published"],
        "counted": state["counted"],
        "created_at": r.created_at.isoformat(),
    }
    if comment:
        view["comment"] = r.comment
    return view


def job_ratings_view(actor: Any, job: Any, *, now: datetime | None = None) -> dict[str, Any]:
    """What the viewer may see about this job's ratings."""
    now = now or timezone.now()
    rows = list(Rating.objects.filter(job=job))
    states = _states(rows, now=now)
    by_side = {r.side: r for r in rows}
    if job_authz.is_admin(actor):
        return {
            "can_rate": False,
            "side": None,
            "ratings": [_rating_view(r, states[str(r.id)], comment=True) for r in rows],
        }
    side = side_for(actor, job)
    if side is None:
        raise NotRatingParty()
    side_code = side[0]
    other = (
        RatingSide.OPERATOR_RATES_BUSINESS
        if side_code == RatingSide.BUSINESS_RATES_OPERATOR
        else RatingSide.BUSINESS_RATES_OPERATOR
    )
    mine = by_side.get(side_code)
    about_me = by_side.get(other)
    remaining = _window() - job_facts.time_in_completed([job.id], now=now)[str(job.id)]
    open_now = job.status == JobStatus.COMPLETED and remaining > timedelta(0)
    return {
        "can_rate": mine is None and open_now,
        "side": side_code,
        "closes_in_seconds": int(remaining.total_seconds()) if open_now else 0,
        "mine": _rating_view(mine, states[str(mine.id)], comment=True) if mine else None,
        "about_me": (
            _rating_view(about_me, states[str(about_me.id)], comment=False)
            if about_me is not None and states[str(about_me.id)]["published"]
            else None
        ),
    }
