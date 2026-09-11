"""Recipient scoped access (backend + boundary only) — plan §11,
`docs/phase-1/recipient-access.md`, the Founder Gate amendment (§0) on
`recipient_access_link` uniqueness.

The recipient is **not** a platform user. A single-job, time-limited,
revocable link is the only door in. This module owns:

* token issuance / atomic revoke-then-replace (the amended uniqueness model —
  **no** `now()` in a partial index; `UNIQUE(job_id)` + request-time checks);
* `RecipientPrincipal` resolution — a non-`User` authz subject scoped to
  exactly one job, with a fixed capability ceiling (`VIEW`, `CONFIRM_RECEIPT`,
  `REPORT_ISSUE`); real-time gating (e.g. "can only confirm receipt while
  `AT_DESTINATION`") is the underlying transition's own guards, not a
  narrowed capability list;
* the minimal-disclosure read;
* `CONFIRM_RECEIPT` → the *same* `JobLifecycleService.transition(DELIVERED)`
  and proof model the driver uses, just a different actor
  (recipient-access.md §4.1);
* `REPORT_ISSUE` → the append-only issue-report **boundary**
  (`RecipientReportedIssue`, ADR-2D-17) — it does not touch `job.status`; the
  Incidents app (plan §19 Step 8, not built) is what triages it.

No HTTP routes here (plan §19 Step 10); no recipient frontend (2D).
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone

from fikisha.audit import services as audit
from fikisha.common.ratelimit import RateLimiter
from fikisha.jobs.constants import (
    JobStatus,
    ProofCapturedBy,
    RecipientAllowedAction,
    RecipientIssueCategory,
)
from fikisha.jobs.errors import (
    RecipientActionNotAllowed,
    RecipientLinkInactive,
    RecipientLinkNotFound,
)
from fikisha.jobs.models import Job, RecipientAccessLink, RecipientReportedIssue
from fikisha.jobs.selectors import job_for_update
from fikisha.jobs.service import TransitionContext
from fikisha.jobs.service import transition as job_transition
from fikisha.outbox.services import emit

_ALL_ACTIONS: list[str] = [
    RecipientAllowedAction.VIEW,
    RecipientAllowedAction.CONFIRM_RECEIPT,
    RecipientAllowedAction.REPORT_ISSUE,
]
_ROLLING_TTL = timedelta(days=7)  # pre-COMPLETED, bumped on each reissue


# ─── RecipientPrincipal — a non-User authz subject (identity.authz.actors.Actor
#     duck-type: is_authenticated / user / roles / is_admin / audit_role) ─────
@dataclass(frozen=True, slots=True)
class RecipientPrincipal:
    link_id: str
    job_id: str
    allowed_actions: tuple[str, ...]

    is_authenticated: bool = False
    user: Any = None
    roles: frozenset[str] = frozenset()
    is_admin: bool = False

    @property
    def audit_role(self) -> str:
        return "RECIPIENT"

    def can(self, action: str) -> bool:
        return action in self.allowed_actions


# ─── token primitives ─────────────────────────────────────────────────
def _new_token() -> str:
    return secrets.token_urlsafe(32)  # 256 bits


def _token_lookup(token: str) -> bytes:
    """HMAC-SHA256 with the server secret key — an indexable value that a DB
    leak alone cannot correlate or brute-force (recipient-access.md §2)."""
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"), token.encode("utf-8"), hashlib.sha256
    ).digest()


def _expiry_for(job: Job) -> Any:
    """recipient-access.md §2: until COMPLETED, a rolling window bumped on each
    reissue; once COMPLETED, ``completed_at + post_completion_window``."""
    if job.completed_at is not None:
        from fikisha.platform_config import services as config

        window = config.get("timeouts.post_completion_window", {}) or {}
        if job.is_high_value or job.latent_risk_cargo:
            hours = float(window.get("high_and_latent_days", 7)) * 24.0
        else:
            hours = float(window.get("default_hours", 72))
        return job.completed_at + timedelta(hours=hours)
    return timezone.now() + _ROLLING_TTL


def issue_or_refresh_link_locked(*, job: Job, actor: Any) -> tuple[RecipientAccessLink, str]:
    """Create the link for an **already job-row-locked** ``job``. Revokes +
    deletes any existing row first (the audit entry is the permanent record of
    the revoked row once it is gone) — the Founder Gate amendment: plain
    ``UNIQUE(job_id)``, no ``now()`` in a partial index."""
    existing = RecipientAccessLink.objects.select_for_update().filter(job=job).first()
    if existing is not None:
        existing.revoked_at = timezone.now()
        existing.revoke_reason = "reissued"
        existing.save(update_fields=["revoked_at", "revoke_reason", "updated_at"])
        audit.record(
            actor=actor,
            action="job.recipient_link.revoked",
            entity_type="recipient_access_link",
            entity_id=existing.id,
            after={"job_id": str(job.id), "reason": "reissued"},
        )
        existing.delete()

    token = _new_token()
    link = RecipientAccessLink.objects.create(
        job=job,
        token_hash=make_password(token),
        token_lookup=_token_lookup(token),
        allowed_actions=_ALL_ACTIONS,
        expires_at=_expiry_for(job),
    )
    if job.recipient_phone:
        link.sent_to_phone = job.recipient_phone
        link.sent_at = timezone.now()
        link.channel_sent = ["SMS"]
        link.save(update_fields=["sent_to_phone", "sent_at", "channel_sent", "updated_at"])

    audit.record(
        actor=actor,
        action="job.recipient_link.issued",
        entity_type="recipient_access_link",
        entity_id=link.id,
        after={"job_id": str(job.id), "expires_at": link.expires_at.isoformat()},
    )
    emit(
        event_type="RecipientLinkIssued",
        aggregate_type="job",
        aggregate_id=str(job.id),
        payload={"job_id": str(job.id), "link_id": str(link.id)},  # never the token
    )
    return link, token


def reissue_link(*, job_id: Any, actor: Any = None) -> tuple[RecipientAccessLink, str]:
    """Standalone, atomic revoke-then-replace: locks the job row, then the
    (possibly absent) existing link row, in one transaction. Concurrent callers
    serialise on the job-row lock — exactly one live link survives."""
    with transaction.atomic():
        job = job_for_update(job_id)
        return issue_or_refresh_link_locked(job=job, actor=actor)


# ─── resolution (request-time checks, in the amendment's exact order) ────
@transaction.atomic
def resolve_recipient(token: str) -> RecipientPrincipal:
    """(1) token resolves via ``token_lookup`` -> a link row; (2) ``revoked_at
    IS NULL``; (3) ``now() < expires_at``; action-membership is checked by
    ``_require`` at the point of use. Every outcome — found-and-active,
    not-found, revoked, expired — is audited (replay/abuse detection)."""
    lookup = _token_lookup(token)
    link = RecipientAccessLink.objects.filter(token_lookup=lookup).select_related("job").first()

    if link is None or not check_password(token, link.token_hash):
        audit.record(
            actor=None,
            action="job.recipient_link.resolve_failed",
            entity_type="recipient_access_link",
            entity_id=None,
            after={"reason": "not_found"},
        )
        raise RecipientLinkNotFound()
    if link.revoked_at is not None or timezone.now() >= link.expires_at:
        audit.record(
            actor=None,
            action="job.recipient_link.resolve_failed",
            entity_type="recipient_access_link",
            entity_id=link.id,
            after={
                "reason": "revoked" if link.revoked_at else "expired",
                "job_id": str(link.job_id),
            },
        )
        raise RecipientLinkInactive()

    principal = RecipientPrincipal(
        link_id=str(link.id), job_id=str(link.job_id), allowed_actions=tuple(link.allowed_actions)
    )
    audit.record(
        actor=principal,
        action="job.recipient_link.resolved",
        entity_type="recipient_access_link",
        entity_id=link.id,
        after={"job_id": principal.job_id},
    )
    return principal


def _require(principal: RecipientPrincipal, action: str) -> None:
    if principal.can(action):
        return
    with transaction.atomic():
        audit.record(
            actor=principal,
            action="job.recipient_link.action_denied",
            entity_type="recipient_access_link",
            entity_id=principal.link_id,
            after={"job_id": principal.job_id, "action": action},
        )
    raise RecipientActionNotAllowed()


def _recheck_link_active(principal: RecipientPrincipal) -> RecipientAccessLink:
    """Re-verify the link is still resolvable and active at the moment of an
    action — a ``principal`` may be held across a request; the link could have
    been revoked or replaced since it was resolved."""
    try:
        link = RecipientAccessLink.objects.get(id=principal.link_id)
    except RecipientAccessLink.DoesNotExist as exc:
        raise RecipientLinkInactive() from exc
    if str(link.job_id) != principal.job_id:  # defence in depth; cannot happen via this API
        raise RecipientLinkInactive()
    if link.revoked_at is not None or timezone.now() >= link.expires_at:
        raise RecipientLinkInactive()
    return link


# ─── minimal-disclosure read (plan §11 — exactly this field set) ─────────
_STATUS_LABELS = dict(JobStatus.choices)


def _first_name_last_initial(full_name: str) -> str:
    parts = (full_name or "").split()
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]} {parts[-1][0]}."


@transaction.atomic
def view(*, principal: RecipientPrincipal) -> dict[str, Any]:
    _require(principal, RecipientAllowedAction.VIEW)
    from fikisha.jobs.selectors import get_job
    from fikisha.verification.models import Domain
    from fikisha.verification.services import subject_meets

    _recheck_link_active(principal)
    job = get_job(principal.job_id)
    cargo_summary = job.cargo.description if job.cargo is not None else ""
    assignment = job.assignment
    driver_first_name = ""
    vehicle_class = ""
    plate = ""
    operator_identity_verified = False
    if assignment is not None:
        driver = assignment.assigned_driver_profile
        driver_first_name = (driver.full_name or "").split()[0] if driver.full_name else ""
        vehicle_class = getattr(assignment.vehicle.vehicle_class, "name_en", "")
        plate = assignment.vehicle.registration
        operator_identity_verified = subject_meets(driver, [Domain.IDENTITY])

    audit.record(
        actor=principal,
        action="job.recipient.viewed",
        entity_type="job",
        entity_id=job.id,
        after={"link_id": principal.link_id},
    )
    return {
        "delivery_reference": job.id.hex[-8:].upper(),
        "recipient_display_name": _first_name_last_initial(job.recipient_name),
        "cargo_summary": cargo_summary[:200],
        "status": job.status,
        "status_label": _STATUS_LABELS.get(job.status, job.status),
        "driver_first_name": driver_first_name,
        "vehicle_class": vehicle_class,
        "vehicle_plate": plate,
        "operator_identity_verified": operator_identity_verified,
        "allowed_actions": list(principal.allowed_actions),
    }


# ─── CONFIRM_RECEIPT — the same DELIVERED transition + proof model ───────
def confirm_receipt(
    *,
    principal: RecipientPrincipal,
    code: str,
    party_name: str,
    signature_evidence_id: Any = None,
    photo_evidence_ids: list[Any] | None = None,
    idempotency_key: str = "",
) -> dict[str, Any]:
    """Requires the recipient OTP (a forwarded link alone cannot confirm —
    recipient-access.md §4.1 / §5) plus a typed name. Calls the identical
    `AT_DESTINATION -> DELIVERED` transition the driver uses; only the actor and
    `captured_by` differ."""
    _require(principal, RecipientAllowedAction.CONFIRM_RECEIPT)
    from fikisha.jobs import otp as otp_service
    from fikisha.jobs.selectors import get_job

    link = _recheck_link_active(principal)
    if link.used_at is not None:
        raise RecipientActionNotAllowed()

    job_id = principal.job_id
    cid = otp_service.verify_otp(
        job=get_job(job_id),
        purpose="RECIPIENT_VERIFY",
        code=code,
        actor=principal,
        consume=False,
    )
    view_out = job_transition(
        job_id=job_id,
        to=JobStatus.DELIVERED,
        actor=principal,
        context=TransitionContext(
            data={
                "initiator_tokens": [],
                "recipient_principal": principal,
                "party_name": party_name,
                "otp_verified": True,
                "_otp_challenge_id": cid,
                "_otp_purpose": "RECIPIENT_VERIFY",
                "signature_evidence_id": signature_evidence_id,
                "photo_evidence_ids": photo_evidence_ids or [],
                "captured_by": ProofCapturedBy.RECIPIENT,
            }
        ),
        idempotency_key=idempotency_key,
    )
    link.used_at = timezone.now()
    link.save(update_fields=["used_at", "updated_at"])
    return view_out


# ─── REPORT_ISSUE — append-only capture, no OTP, no job.status change ────
def report_issue(
    *,
    principal: RecipientPrincipal,
    category: str,
    description: str = "",
    other_label: str = "",
    photo_evidence_ids: list[Any] | None = None,
) -> dict[str, Any]:
    """recipient-access.md §4.2: **no OTP required**; rate-limited. Records the
    report append-only. Does not move job.status — see ADR-2D-17."""
    _require(principal, RecipientAllowedAction.REPORT_ISSUE)
    if category not in RecipientIssueCategory.values:
        raise RecipientActionNotAllowed()
    _recheck_link_active(principal)

    RateLimiter(scope="recipient_issue", limit=5, window_seconds=3600).check(principal.link_id)

    with transaction.atomic():
        from fikisha.jobs.selectors import get_job

        job = get_job(principal.job_id)
        report = RecipientReportedIssue.objects.create(
            job=job,
            reported_via_link_id=principal.link_id,
            category=category,
            other_label=other_label.strip(),
            description=description.strip(),
            photo_evidence_ids=list(photo_evidence_ids or []),
        )
        audit.record(
            actor=principal,
            action="job.recipient.reported_issue",
            entity_type="recipient_reported_issue",
            entity_id=report.id,
            after={"job_id": str(job.id), "category": category},
        )
        emit(
            event_type="RecipientRaisedIssue",
            aggregate_type="job",
            aggregate_id=str(job.id),
            payload={
                "job_id": str(job.id),
                "report_id": str(report.id),
                "category": category,
            },
        )
    return {"report_id": str(report.id), "category": category}
