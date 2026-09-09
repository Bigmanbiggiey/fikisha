"""Verification data model (Phase 1 database-design §4.4, verification-architecture).

- ``VerificationRecord`` — one per (subject, domain); ``state`` is a cache.
- ``VerificationDecision`` — append-only; the authoritative history of what was
  submitted / reviewed / decided, by whom, when.
- ``VerificationEvidence`` — links an ``evidence.EvidenceObject`` to a record,
  with its own document dates; superseded (not deleted) when replaced.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.db import models
from django.utils import timezone

from fikisha.common.models import AppendOnlyModel, AppendOnlyQuerySet, TimestampedModel


class SubjectType(models.TextChoices):
    OPERATOR = "OPERATOR", "Operator"
    VEHICLE = "VEHICLE", "Vehicle"
    BASE = "BASE", "Operating location"


class Domain(models.TextChoices):
    IDENTITY = "IDENTITY", "Identity"
    LICENCE = "LICENCE", "Driving licence"
    GOOD_CONDUCT = "GOOD_CONDUCT", "Certificate of Good Conduct"
    VEHICLE = "VEHICLE", "Vehicle (registration / roadworthiness)"
    HEAVY_CLASS_COMPLIANCE = "HEAVY_CLASS_COMPLIANCE", "Heavy-class compliance"
    ASSOCIATION = "ASSOCIATION", "Vehicle / operator association"
    BASE = "BASE", "Operating base"
    DOCUMENT = "DOCUMENT", "Supporting document"
    HISTORY = "HISTORY", "Platform history"  # derived, feeds trust — not submitted in 2C


class State(models.TextChoices):
    NOT_SUBMITTED = "NOT_SUBMITTED", "Not submitted"
    SUBMITTED = "SUBMITTED", "Submitted"
    IN_REVIEW = "IN_REVIEW", "In review"
    INFO_REQUESTED = "INFO_REQUESTED", "More info requested"
    VERIFIED = "VERIFIED", "Verified"
    REJECTED = "REJECTED", "Rejected"
    EXPIRED = "EXPIRED", "Expired"


class Action(models.TextChoices):
    SUBMIT = "SUBMIT", "Submit"
    START_REVIEW = "START_REVIEW", "Start review"
    REQUEST_INFO = "REQUEST_INFO", "Request info"
    APPROVE = "APPROVE", "Approve"
    REJECT = "REJECT", "Reject"
    EXPIRE = "EXPIRE", "Expire (system)"
    RENEW = "RENEW", "Renew"


VALID_DOMAINS_BY_SUBJECT: dict[str, set[str]] = {
    SubjectType.OPERATOR: {Domain.IDENTITY, Domain.LICENCE, Domain.GOOD_CONDUCT, Domain.DOCUMENT},
    SubjectType.VEHICLE: {
        Domain.VEHICLE,
        Domain.HEAVY_CLASS_COMPLIANCE,
        Domain.ASSOCIATION,
        Domain.DOCUMENT,
    },
    SubjectType.BASE: {Domain.BASE, Domain.DOCUMENT},
}


class VerificationRecord(TimestampedModel):
    subject_type = models.CharField(max_length=12, choices=SubjectType.choices)
    subject_operator = models.ForeignKey(
        "operators.OperatorProfile",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="verification_records",
    )
    subject_vehicle = models.ForeignKey(
        "vehicles.Vehicle",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="verification_records",
    )
    subject_base = models.ForeignKey(
        "operators.OperatingBase",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="verification_records",
    )
    domain = models.CharField(max_length=32, choices=Domain.choices)
    state = models.CharField(max_length=16, choices=State.choices, default=State.NOT_SUBMITTED)
    issuing_authority = models.CharField(max_length=120, blank=True, default="")
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    owner_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_decision = models.ForeignKey(
        "verification.VerificationDecision",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        db_table = "verification_record"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        subject_operator__isnull=False,
                        subject_vehicle__isnull=True,
                        subject_base__isnull=True,
                    )
                    | models.Q(
                        subject_operator__isnull=True,
                        subject_vehicle__isnull=False,
                        subject_base__isnull=True,
                    )
                    | models.Q(
                        subject_operator__isnull=True,
                        subject_vehicle__isnull=True,
                        subject_base__isnull=False,
                    )
                ),
                name="verification_record_exactly_one_subject",
            ),
            models.UniqueConstraint(
                fields=["subject_operator", "domain"],
                condition=models.Q(subject_operator__isnull=False),
                name="uniq_operator_domain",
            ),
            models.UniqueConstraint(
                fields=["subject_vehicle", "domain"],
                condition=models.Q(subject_vehicle__isnull=False),
                name="uniq_vehicle_domain",
            ),
            models.UniqueConstraint(
                fields=["subject_base", "domain"],
                condition=models.Q(subject_base__isnull=False),
                name="uniq_base_domain",
            ),
        ]
        indexes = [
            models.Index(fields=["state"]),
            models.Index(fields=["subject_type", "domain", "state"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.subject_type}:{self.domain} [{self.state}]"

    @property
    def subject_id(self) -> object:
        return self.subject_operator_id or self.subject_vehicle_id or self.subject_base_id

    def effective_state(self, *, now: Any = None) -> str:
        """Deterministic current state — folds expiry in without a sweep."""
        if self.state == State.VERIFIED and self.expires_at is not None:
            if self.expires_at <= (now or timezone.now()):
                return State.EXPIRED
        return self.state

    def is_currently_valid(self, *, now: Any = None) -> bool:
        return self.effective_state(now=now) == State.VERIFIED


class VerificationDecision(AppendOnlyModel):
    record = models.ForeignKey(
        VerificationRecord, on_delete=models.CASCADE, related_name="decisions"
    )
    action = models.CharField(max_length=16, choices=Action.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    actor_role = models.CharField(max_length=40, blank=True, default="")
    reason = models.TextField(blank=True, default="")
    note = models.TextField(blank=True, default="")
    set_expires_at = models.DateTimeField(null=True, blank=True)

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        db_table = "verification_decision"
        ordering = ["created_at"]
        indexes = [models.Index(fields=["record", "created_at"])]

    def __str__(self) -> str:
        return f"{self.action} on {self.record_id}"


class EvidenceKind(models.TextChoices):
    NATIONAL_ID = "NATIONAL_ID", "National ID"
    PASSPORT = "PASSPORT", "Passport"
    SELFIE = "SELFIE", "Selfie / photo"
    DRIVING_LICENCE = "DRIVING_LICENCE", "Driving licence"
    GOOD_CONDUCT_CERT = "GOOD_CONDUCT_CERT", "Certificate of Good Conduct"
    LOGBOOK = "LOGBOOK", "Logbook / registration"
    INSPECTION_CERT = "INSPECTION_CERT", "Inspection certificate"
    INSURANCE_CERT = "INSURANCE_CERT", "Insurance certificate"
    NTSA_OPERATOR_LICENCE = "NTSA_OPERATOR_LICENCE", "NTSA commercial operator licence"
    SPEED_LIMITER_CERT = "SPEED_LIMITER_CERT", "Speed-limiter certificate"
    TELEMATICS_CERT = "TELEMATICS_CERT", "Telematics certificate"
    OWNER_CONSENT = "OWNER_CONSENT", "Owner consent (authorised driver)"
    VEHICLE_PHOTO = "VEHICLE_PHOTO", "Vehicle photo"
    PLATE_PHOTO = "PLATE_PHOTO", "Number-plate photo"
    BASE_PHOTO = "BASE_PHOTO", "Operating-location photo"
    OTHER = "OTHER", "Other document"


class VerificationEvidence(TimestampedModel):
    record = models.ForeignKey(
        VerificationRecord, on_delete=models.CASCADE, related_name="evidence"
    )
    evidence_object = models.ForeignKey(
        "evidence.EvidenceObject", on_delete=models.PROTECT, related_name="+"
    )
    kind = models.CharField(max_length=32, choices=EvidenceKind.choices)
    issued_at = models.DateField(null=True, blank=True)
    expires_at = models.DateField(null=True, blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    superseded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "verification_evidence"
        ordering = ["-submitted_at"]
        indexes = [models.Index(fields=["record", "superseded_at"])]

    def __str__(self) -> str:
        return f"{self.kind} for {self.record_id}"

    @property
    def is_current(self) -> bool:
        return self.superseded_at is None
