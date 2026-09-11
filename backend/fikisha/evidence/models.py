"""Evidence object metadata + the append-only HIGH-PII access log
(Phase 1 database-design §4.13).
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from fikisha.common.models import AppendOnlyModel, AppendOnlyQuerySet, TimestampedModel


class PiiClass(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"


class EvidencePurpose(models.TextChoices):
    VERIFICATION_DOC = "VERIFICATION_DOC", "Verification document"
    VEHICLE_PHOTO = "VEHICLE_PHOTO", "Vehicle photo"
    PROFILE_PHOTO = "PROFILE_PHOTO", "Profile photo"
    BASE_PHOTO = "BASE_PHOTO", "Operating-location photo"
    # Phase 2D Step 8 (Incidents & Disputes) — additive; no existing member
    # changes, no migration needed (a plain CharField, no DB check constraint).
    INCIDENT_EVIDENCE = "INCIDENT_EVIDENCE", "Incident evidence"


class UploaderKind(models.TextChoices):
    OPERATOR = "OPERATOR", "Operator"
    BUSINESS = "BUSINESS", "Business user"
    ADMIN = "ADMIN", "Administrator"
    SYSTEM = "SYSTEM", "System"
    # Phase 2D Step 8 — a recipient may attach evidence to an incident (FR-D-2).
    RECIPIENT = "RECIPIENT", "Recipient"


class EvidenceObject(TimestampedModel):
    storage_key = models.CharField(max_length=300, unique=True)
    content_type = models.CharField(max_length=120)
    size_bytes = models.BigIntegerField()
    sha256 = models.CharField(max_length=64)
    pii_class = models.CharField(max_length=8, choices=PiiClass.choices, default=PiiClass.MEDIUM)
    purpose = models.CharField(max_length=32, choices=EvidencePurpose.choices)
    # Generic link to the owning domain row (this module depends on nothing).
    linked_entity_type = models.CharField(max_length=60, blank=True, default="")
    linked_entity_id = models.UUIDField(null=True, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    uploaded_by_kind = models.CharField(
        max_length=12, choices=UploaderKind.choices, default=UploaderKind.OPERATOR
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "evidence_object"
        indexes = [
            models.Index(fields=["linked_entity_type", "linked_entity_id"]),
            models.Index(fields=["purpose"]),
        ]

    def __str__(self) -> str:
        return f"{self.purpose} {self.id}"

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class EvidenceAccessLog(AppendOnlyModel):
    """One row per fetch of a HIGH-PII evidence object (Phase 0 NFR-SEC-4)."""

    evidence_object = models.ForeignKey(
        EvidenceObject, on_delete=models.CASCADE, related_name="access_log"
    )
    accessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    accessed_by_role = models.CharField(max_length=40, blank=True, default="")
    reason = models.CharField(max_length=200, blank=True, default="")

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        db_table = "evidence_access_log"
        indexes = [models.Index(fields=["evidence_object", "created_at"])]

    def __str__(self) -> str:
        return f"access {self.evidence_object_id} by {self.accessed_by_id}"
