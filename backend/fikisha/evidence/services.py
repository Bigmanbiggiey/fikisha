"""EvidenceService — store, stat, stream, and delete private evidence objects.

Bytes go through the Phase 2A ``storage`` abstraction. This module authorizes
nothing itself — the consuming module (Verification) checks the caller *before*
calling ``open_stream`` / ``store``; ``open_stream`` records the HIGH-PII access
log row.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, BinaryIO

from django.db import transaction

from fikisha.evidence.models import EvidenceAccessLog, EvidenceObject, PiiClass, UploaderKind
from fikisha.storage.service import get_storage

# Per-purpose upload rules (evidence-storage.md §3).
_ALLOWED_TYPES: dict[str, set[str]] = {
    "VERIFICATION_DOC": {"image/jpeg", "image/png", "application/pdf"},
    "VEHICLE_PHOTO": {"image/jpeg", "image/png", "image/webp"},
    "PROFILE_PHOTO": {"image/jpeg", "image/png", "image/webp"},
    "BASE_PHOTO": {"image/jpeg", "image/png", "image/webp"},
}
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB


class EvidenceValidationError(ValueError):
    """Raised when an upload violates the per-purpose type / size allowlist."""


def _key(purpose: str, object_id: uuid.UUID) -> str:
    now = datetime.now(UTC)
    return f"evidence/{purpose.lower()}/{now:%Y/%m}/{object_id}"


@transaction.atomic
def store(
    *,
    data: bytes | BinaryIO,
    content_type: str,
    purpose: str,
    pii_class: str = PiiClass.MEDIUM,
    linked_entity_type: str = "",
    linked_entity_id: Any | None = None,
    uploaded_by: Any | None = None,
    uploaded_by_kind: str = UploaderKind.OPERATOR,
) -> EvidenceObject:
    payload = data if isinstance(data, bytes) else data.read()
    if not payload:
        raise EvidenceValidationError("Empty upload.")
    if len(payload) > _MAX_BYTES:
        raise EvidenceValidationError("File is too large (max 10 MB).")
    allowed = _ALLOWED_TYPES.get(purpose)
    if allowed is not None and content_type not in allowed:
        raise EvidenceValidationError(
            f"{content_type!r} is not allowed for {purpose} (allowed: {sorted(allowed)})."
        )

    object_id = uuid.uuid4()
    key = _key(purpose, object_id)
    stored = get_storage().put(key, payload, content_type=content_type)

    return EvidenceObject.objects.create(
        id=object_id,
        storage_key=stored.key,
        content_type=content_type,
        size_bytes=stored.size,
        sha256=stored.sha256,
        pii_class=pii_class,
        purpose=purpose,
        linked_entity_type=linked_entity_type,
        linked_entity_id=linked_entity_id,
        uploaded_by=uploaded_by if getattr(uploaded_by, "pk", None) else None,
        uploaded_by_kind=uploaded_by_kind,
    )


def open_stream(
    obj: EvidenceObject, *, actor_user: Any | None, actor_role: str = "", reason: str = ""
) -> tuple[bytes, str]:
    """Return ``(bytes, content_type)`` for an already-authorized fetch.

    Writes an ``EvidenceAccessLog`` row for HIGH-PII objects (NFR-SEC-4).
    """
    if obj.is_deleted:
        raise FileNotFoundError("Evidence object has been purged.")
    payload = get_storage().open(obj.storage_key).read()
    if obj.pii_class == PiiClass.HIGH:
        with transaction.atomic():
            EvidenceAccessLog.objects.create(
                evidence_object=obj,
                accessed_by=actor_user if getattr(actor_user, "pk", None) else None,
                accessed_by_role=actor_role,
                reason=reason[:200],
            )
    return payload, obj.content_type
