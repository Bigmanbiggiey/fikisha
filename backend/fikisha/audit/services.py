"""Audit service — the only supported way to write an audit entry.

``record(...)`` MUST be called inside a database transaction so the audit row is
atomic with the change it records (Phase 1 NFR-AUD-1). It:
  * resolves the actor -> (user, role),
  * redacts HIGH-PII from ``before`` / ``after``,
  * locks the chain head, computes a gapless ``seq`` and ``prev_hash``,
  * computes ``row_hash = sha256(seq \\n prev_hash \\n canonical_json(payload))``,
  * inserts the append-only row and advances the head.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from django.db import transaction

from fikisha.audit.models import ActorRole, AuditChainHead, AuditLogEntry, SourceChannel
from fikisha.common.request_id import get_request_id

_REDACT_KEYS = {
    "password",
    "secret",
    "token",
    "token_hash",
    "access_token",
    "refresh_token",
    "code",
    "code_hash",
    "otp",
    "otp_code",
    "id_number",
    "national_id",
    "payout_number",
    "signature",
    "signed_url",
}
_REDACTED = "[redacted]"


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: (_REDACTED if k.lower() in _REDACT_KEYS else _redact(v)) for k, v in value.items()
        }
    if isinstance(value, list | tuple):
        return [_redact(v) for v in value]
    return value


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _hash(seq: int, prev_hash: str, payload: dict[str, Any]) -> str:
    material = f"{seq}\n{prev_hash}\n{_canonical(payload)}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _resolve_actor(actor: Any) -> tuple[Any, str]:
    """Return ``(user_or_None, role_str)`` from a User, an authz Actor, or None."""
    if actor is None:
        return None, ActorRole.SYSTEM
    # authz Actor duck-typing
    user = getattr(actor, "user", None)
    role = getattr(actor, "audit_role", None)
    if role is not None:
        return user, role
    # a Django user instance
    if hasattr(actor, "pk"):
        is_admin = bool(getattr(actor, "is_staff", False)) or hasattr(actor, "admin_profile")
        return actor, (ActorRole.PLATFORM_ADMIN if is_admin else ActorRole.BUSINESS)
    return None, ActorRole.SYSTEM


def record(
    *,
    actor: Any,
    action: str,
    entity_type: str,
    entity_id: Any | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    source_channel: str = SourceChannel.API,
    source_ip: str | None = None,
    source_device: str | None = None,
) -> AuditLogEntry:
    # Deliberately NOT wrapped in its own ``transaction.atomic`` — the audit row
    # must be atomic with the *caller's* state change, so the caller opens the
    # transaction. This guard makes a non-transactional call fail loudly.
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError(
            "audit.record() must be called inside a database transaction "
            "(wrap the state change + audit in transaction.atomic())."
        )

    user, role = _resolve_actor(actor)
    request_id = get_request_id()

    head, _ = AuditChainHead.objects.select_for_update().get_or_create(pk=1)
    seq = head.last_seq + 1
    prev_hash = head.last_hash

    payload = {
        "seq": seq,
        "actor_user": str(getattr(user, "pk", None)) if user is not None else None,
        "actor_role": str(role),
        "action": action,
        "entity_type": entity_type,
        "entity_id": str(entity_id) if entity_id is not None else None,
        "before": _redact(before),
        "after": _redact(after),
        "request_id": request_id,
        "source_channel": source_channel,
    }
    row_hash = _hash(seq, prev_hash, payload)

    entry = AuditLogEntry(
        seq=seq,
        actor_user=user if user is not None and getattr(user, "pk", None) else None,
        actor_role=role,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before=_redact(before),
        after=_redact(after),
        request_id=request_id,
        source_channel=source_channel,
        source_ip=source_ip,
        source_device=source_device,
        prev_hash=prev_hash,
        row_hash=row_hash,
    )
    entry.save()

    head.last_seq = seq
    head.last_hash = row_hash
    head.save(update_fields=["last_seq", "last_hash", "updated_at"])
    return entry


def verify_chain(*, start: int = 1, end: int | None = None) -> list[dict[str, Any]]:
    """Walk the chain, recompute hashes, and return a list of detected breaks."""
    qs = AuditLogEntry.objects.all().order_by("seq")
    if start > 1:
        qs = qs.filter(seq__gte=start)
    if end is not None:
        qs = qs.filter(seq__lte=end)

    breaks: list[dict[str, Any]] = []
    expected_prev = ""
    expected_seq: int | None = None
    for row in qs.iterator():
        if expected_seq is not None and row.seq != expected_seq:
            breaks.append({"seq": row.seq, "issue": "gap_or_reorder", "expected_seq": expected_seq})
        if start == 1 and row.prev_hash != expected_prev and expected_seq is not None:
            breaks.append({"seq": row.seq, "issue": "prev_hash_mismatch"})
        payload = {
            "seq": row.seq,
            "actor_user": str(row.actor_user_id) if row.actor_user_id else None,
            "actor_role": row.actor_role,
            "action": row.action,
            "entity_type": row.entity_type,
            "entity_id": str(row.entity_id) if row.entity_id else None,
            "before": row.before,
            "after": row.after,
            "request_id": row.request_id,
            "source_channel": row.source_channel,
        }
        recomputed = _hash(row.seq, row.prev_hash, payload)
        if recomputed != row.row_hash:
            breaks.append({"seq": row.seq, "issue": "row_hash_mismatch"})
        expected_prev = row.row_hash
        expected_seq = row.seq + 1
    return breaks
