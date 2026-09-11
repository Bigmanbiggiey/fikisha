"""Job domain model — Phase 2D.

Schema follows ``docs/phase-1/database-design.md §4.6-4.11`` with the
Founder-approved Phase 2D amendments (plan §0):
  * locations use plain ``DecimalField`` lat/lng + ``geo_state`` — **no PostGIS**
    (ADR-2D-10);
  * ``recipient_access_link`` uses a plain ``UNIQUE(job_id)`` — no time-dependent
    partial index; "active" is evaluated at request time (Founder amendment);
  * ``DISPUTED → RESUME`` is not implemented; ``Dispute.pre_dispute_status`` is
    persisted so a future founder-approved rule is deterministic (ADR-2D-07).

Money columns are ``*_kes`` BigInteger, KES minor units (NFR-INT-3).
``JobLifecycleService.transition()`` is the only writer of ``Job.status``.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.db import models

from fikisha.common.models import AppendOnlyModel, AppendOnlyQuerySet, TimestampedModel
from fikisha.jobs.constants import (
    AssignedBy,
    Attestation,
    CancellationReason,
    ConfirmationMethod,
    GeoState,
    HighValueDecision,
    JobEventCategory,
    JobEventType,
    JobStatus,
    LocationSourceKind,
    LocationType,
    OperatorParty,
    OtpPurpose,
    PenaltyClass,
    ProofCapturedBy,
    ProofKind,
    RecipientIssueCategory,
    TrustLevel,
    ValueBand,
)


def _coord_field() -> models.DecimalField:
    """A plain lat/lng column (no PostGIS — ADR-2D-10)."""
    return models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)


class CargoDetails(TimestampedModel):
    description = models.TextField()
    category_code = models.CharField(max_length=64, blank=True, default="")
    est_weight_kg = models.PositiveIntegerField(null=True, blank=True)
    dims_l_cm = models.PositiveIntegerField(null=True, blank=True)
    dims_w_cm = models.PositiveIntegerField(null=True, blank=True)
    dims_h_cm = models.PositiveIntegerField(null=True, blank=True)
    declared_value_kes = models.BigIntegerField()
    handling_flags = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "cargo_details"


class VehicleRequirement(TimestampedModel):
    required_vehicle_class_codes = models.JSONField(default=list, blank=True)
    min_payload_kg = models.PositiveIntegerField(default=0)
    min_volume_m3 = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    required_features = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "vehicle_requirement"


class JobLocation(TimestampedModel):
    """Immutable snapshot copied from a business_location (or ad-hoc) at job
    creation, so a later edit to the source does not rewrite job history."""

    type = models.CharField(max_length=12, choices=LocationType.choices)
    source_kind = models.CharField(max_length=20, choices=LocationSourceKind.choices)
    source_location = models.ForeignKey(
        "business.BusinessLocation",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    address_text = models.TextField(blank=True, default="")
    lat = _coord_field()
    lng = _coord_field()
    geo_state = models.CharField(
        max_length=16, choices=GeoState.choices, default=GeoState.NOT_CAPTURED
    )
    zone = models.ForeignKey(
        "platform_config.Zone", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    contact_name = models.CharField(max_length=120, blank=True, default="")
    contact_phone = models.CharField(max_length=32, blank=True, default="")
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "job_location"


class Job(TimestampedModel):
    """Aggregate root. The only row a client mutates concurrently; the
    ``version`` column backs ``If-Match`` optimistic concurrency."""

    business = models.ForeignKey(
        "business.BusinessAccount", on_delete=models.PROTECT, related_name="jobs"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    status = models.CharField(
        max_length=16, choices=JobStatus.choices, default=JobStatus.DRAFT, db_index=True
    )
    version = models.PositiveIntegerField(default=0)

    pickup_location = models.ForeignKey(
        JobLocation, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    destination_location = models.ForeignKey(
        JobLocation, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    recipient_name = models.CharField(max_length=120, blank=True, default="")
    recipient_phone = models.CharField(max_length=32, blank=True, default="")

    cargo = models.ForeignKey(
        CargoDetails, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    vehicle_requirement = models.ForeignKey(
        VehicleRequirement, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    pickup_datetime = models.DateTimeField(null=True, blank=True)
    delivery_requirements = models.TextField(blank=True, default="")
    delivery_flags = models.JSONField(default=list, blank=True)

    proposed_price_kes = models.BigIntegerField(null=True, blank=True)
    declared_value_kes = models.BigIntegerField(default=0)
    value_band = models.CharField(max_length=12, choices=ValueBand.choices, null=True, blank=True)
    required_trust_level = models.CharField(
        max_length=4, choices=TrustLevel.choices, null=True, blank=True
    )
    is_high_value = models.BooleanField(default=False)
    latent_risk_cargo = models.BooleanField(default=False)

    agreement = models.OneToOneField(
        "jobs.Agreement", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    assignment = models.ForeignKey(
        "jobs.Assignment", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    distance_km = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    config_version = models.ForeignKey(
        "platform_config.PlatformConfigVersion",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )

    published_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    terminal_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "job"
        indexes = [
            models.Index(
                fields=["status", "value_band", "-created_at"],
                name="ix_job_discovery",
                condition=models.Q(status__in=["REQUESTED", "NEGOTIATING"]),
            ),
            models.Index(fields=["business", "status", "-created_at"], name="ix_job_business"),
            models.Index(
                fields=["assignment"],
                name="ix_job_active_assignment",
                condition=models.Q(
                    status__in=[
                        "ASSIGNED",
                        "AT_PICKUP",
                        "PICKED_UP",
                        "IN_TRANSIT",
                        "AT_DESTINATION",
                    ]
                ),
            ),
            models.Index(
                fields=["status"], name="ix_job_disputed", condition=models.Q(status="DISPUTED")
            ),
            models.Index(
                fields=["delivered_at"],
                name="ix_job_delivered",
                condition=models.Q(status="DELIVERED"),
            ),
            models.Index(
                fields=["completed_at"],
                name="ix_job_completed",
                condition=models.Q(status="COMPLETED"),
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(status="DRAFT")
                    | (
                        models.Q(value_band__isnull=False)
                        & models.Q(required_trust_level__isnull=False)
                    )
                ),
                name="ck_job_band_set_once_published",
            ),
        ]

    def __str__(self) -> str:  # pragma: no cover - debug aid
        return f"Job {self.pk} [{self.status}]"


class Agreement(AppendOnlyModel):
    job = models.OneToOneField(Job, on_delete=models.PROTECT, related_name="agreement_row")
    operator_party = models.CharField(max_length=12, choices=OperatorParty.choices)
    operator = models.ForeignKey(
        "operators.OperatorProfile",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    group = models.ForeignKey(
        "groups.OperatorGroup", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    agreed_price_kes = models.BigIntegerField()
    currency = models.CharField(max_length=3, default="KES")
    accepting_entry_ids = models.JSONField(default=list, blank=True)
    terms_note = models.TextField(blank=True, default="")
    version = models.PositiveIntegerField(default=1)
    agreed_at = models.DateTimeField(auto_now_add=True)

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        db_table = "agreement"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(operator__isnull=False, group__isnull=True)
                    | models.Q(operator__isnull=True, group__isnull=False)
                ),
                name="ck_agreement_one_party",
            ),
        ]


class Assignment(TimestampedModel):
    """One row per assignment attempt; ``Job.assignment`` points at the current."""

    job = models.ForeignKey(Job, on_delete=models.PROTECT, related_name="assignments")
    operator_party = models.CharField(max_length=12, choices=OperatorParty.choices)
    operator = models.ForeignKey(
        "operators.OperatorProfile",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    group = models.ForeignKey(
        "groups.OperatorGroup", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    assigned_driver_profile = models.ForeignKey(
        "operators.OperatorProfile", on_delete=models.PROTECT, related_name="driver_assignments"
    )
    vehicle = models.ForeignKey("vehicles.Vehicle", on_delete=models.PROTECT, related_name="+")
    assigned_by = models.CharField(max_length=16, choices=AssignedBy.choices)
    assigned_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    reassigned_from = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    admin_override_reason = models.TextField(blank=True, default="")
    driver_trust_level = models.CharField(max_length=4, choices=TrustLevel.choices)
    config_version = models.ForeignKey(
        "platform_config.PlatformConfigVersion",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "assignment"
        indexes = [models.Index(fields=["job", "-assigned_at"], name="ix_assignment_job")]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(operator__isnull=False, group__isnull=True)
                    | models.Q(operator__isnull=True, group__isnull=False)
                ),
                name="ck_assignment_one_party",
            ),
        ]


class CancellationRecord(AppendOnlyModel):
    job = models.ForeignKey(Job, on_delete=models.PROTECT, related_name="cancellation_records")
    cancelled_by_role = models.CharField(max_length=32)
    cancelled_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    at_status = models.CharField(max_length=16, choices=JobStatus.choices)
    reason_code = models.CharField(
        max_length=32, choices=CancellationReason.choices, default=CancellationReason.OTHER
    )
    reason_text = models.TextField(blank=True, default="")
    penalty_class = models.CharField(
        max_length=20, choices=PenaltyClass.choices, default=PenaltyClass.NONE
    )

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        db_table = "cancellation_record"


class FailureRecord(AppendOnlyModel):
    job = models.ForeignKey(Job, on_delete=models.PROTECT, related_name="failure_records")
    at_status = models.CharField(max_length=16, choices=JobStatus.choices)
    reason_text = models.TextField()
    recorded_by_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        db_table = "failure_record"


class JobEvent(AppendOnlyModel):
    """Append-only, strictly ordered per job (ADR-009 consolidation).
    Views ``job_status_event`` / ``chain_of_custody`` / ``job_timeline`` are
    created in the 0002 migration."""

    job = models.ForeignKey(Job, on_delete=models.PROTECT, related_name="events")
    seq = models.BigIntegerField()
    category = models.CharField(max_length=20, choices=JobEventCategory.choices)
    type = models.CharField(max_length=32, choices=JobEventType.choices)
    is_custody = models.BooleanField(default=False)
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    actor_role = models.CharField(max_length=32, blank=True, default="")
    server_time = models.DateTimeField(auto_now_add=True)
    reported_time = models.DateTimeField(null=True, blank=True)
    from_status = models.CharField(max_length=16, choices=JobStatus.choices, null=True, blank=True)
    to_status = models.CharField(max_length=16, choices=JobStatus.choices, null=True, blank=True)
    lat = _coord_field()
    lng = _coord_field()
    geo_accuracy_m = models.DecimalField(max_digits=8, decimal_places=1, null=True, blank=True)
    geo_state = models.CharField(
        max_length=16, choices=GeoState.choices, default=GeoState.NOT_CAPTURED
    )
    confirmation_method = models.CharField(
        max_length=12, choices=ConfirmationMethod.choices, null=True, blank=True
    )
    evidence_ids = models.JSONField(default=list, blank=True)
    content_hashes = models.JSONField(default=list, blank=True)
    source_meta = models.JSONField(default=dict, blank=True)
    note = models.TextField(blank=True, default="")
    corrects_event = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    config_version = models.ForeignKey(
        "platform_config.PlatformConfigVersion",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        db_table = "job_event"
        constraints = [
            models.UniqueConstraint(fields=["job", "seq"], name="uq_job_event_seq"),
        ]
        indexes = [
            models.Index(fields=["job", "seq"], name="ix_job_event_job_seq"),
            models.Index(
                fields=["job"],
                name="ix_job_event_custody",
                condition=models.Q(is_custody=True),
            ),
        ]


class _ProofBase(AppendOnlyModel):
    kind = models.CharField(max_length=12, choices=ProofKind.choices)
    party_name = models.CharField(max_length=120, blank=True, default="")
    methods = models.JSONField(default=list, blank=True)
    otp_verified = models.BooleanField(default=False)
    signature_evidence_id = models.UUIDField(null=True, blank=True)
    photo_evidence_ids = models.JSONField(default=list, blank=True)
    captured_by = models.CharField(max_length=20, choices=ProofCapturedBy.choices)
    captured_at = models.DateTimeField(auto_now_add=True)
    condition_note = models.TextField(blank=True, default="")
    attestation = models.CharField(
        max_length=32, choices=Attestation.choices, default=Attestation.VERIFIED
    )

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        abstract = True


class ProofOfPickup(_ProofBase):
    job = models.OneToOneField(Job, on_delete=models.PROTECT, related_name="proof_of_pickup")

    class Meta:
        db_table = "proof_of_pickup"


class ProofOfDelivery(_ProofBase):
    job = models.OneToOneField(Job, on_delete=models.PROTECT, related_name="proof_of_delivery")

    class Meta:
        db_table = "proof_of_delivery"


class OtpChallengeBase(TimestampedModel):
    job = models.ForeignKey(Job, on_delete=models.PROTECT, related_name="+")
    purpose = models.CharField(max_length=20, choices=OtpPurpose.choices)
    code_hash = models.CharField(max_length=128)
    sent_to_phone = models.CharField(max_length=32)
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=5)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    @property
    def is_consumed(self) -> bool:
        return self.consumed_at is not None

    @property
    def is_locked(self) -> bool:
        return self.attempts >= self.max_attempts

    def is_expired(self, *, now: Any = None) -> bool:
        from django.utils import timezone

        return self.expires_at <= (now or timezone.now())

    def is_usable(self, *, now: Any = None) -> bool:
        return not (self.is_consumed or self.is_locked or self.is_expired(now=now))


class PickupOtpChallenge(OtpChallengeBase):
    class Meta:
        db_table = "pickup_otp_challenge"


class RecipientAccessLink(TimestampedModel):
    """One live recipient link per job (Founder amendment: plain ``UNIQUE(job)``;
    "active" = ``revoked_at IS NULL AND now() < expires_at``, checked at request
    time; replacement revokes-then-deletes the prior row under the job lock)."""

    job = models.OneToOneField(Job, on_delete=models.PROTECT, related_name="recipient_link")
    token_hash = models.CharField(max_length=128, unique=True)
    token_lookup = models.BinaryField(max_length=64)
    allowed_actions = models.JSONField(default=list, blank=True)
    channel_sent = models.JSONField(default=list, blank=True)
    sent_to_phone = models.CharField(max_length=32, blank=True, default="")
    sent_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoke_reason = models.TextField(blank=True, default="")

    class Meta:
        db_table = "recipient_access_link"
        indexes = [models.Index(fields=["token_lookup"], name="ix_recipient_link_lookup")]


class RecipientOtpChallenge(OtpChallengeBase):
    # nullable: the recipient OTP is issued to ``job.recipient_phone`` on arrival
    # at destination, independent of (and usually before) the recipient access
    # link — which is a later increment (plan §19 Step 7). ADR-2D-16.
    link = models.ForeignKey(
        RecipientAccessLink,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="otp_challenges",
    )

    class Meta:
        db_table = "recipient_otp_challenge"


class RecipientReportedIssue(AppendOnlyModel):
    """The recipient-issue-reporting **boundary** (recipient-access.md §4.2,
    FR-D-2) — append-only capture only. It does **not** move ``job.status`` and
    is not the ``incident`` model: triage, severity, SLA timers, and the
    progression-blocking ``* → DISPUTED`` path are the Incidents app (plan §19
    Step 8, not built). This row is what that later app will read to promote a
    recipient report into a full incident. ADR-2D-17."""

    job = models.ForeignKey(Job, on_delete=models.PROTECT, related_name="recipient_issues")
    # Plain UUID, not a FK: the amended link lifecycle (§0 amendment) deletes a
    # superseded link row on reissue. A FK here — PROTECT blocks the delete;
    # SET_NULL needs Django's delete-collector to call .update(), which
    # AppendOnlyQuerySet refuses even for a cascade. A plain id keeps this
    # append-only report immune to the link's own lifecycle; ``job`` is the
    # real, permanent correlation key.
    reported_via_link_id = models.UUIDField()
    category = models.CharField(max_length=20, choices=RecipientIssueCategory.choices)
    other_label = models.CharField(max_length=80, blank=True, default="")
    description = models.TextField(blank=True, default="")
    photo_evidence_ids = models.JSONField(default=list, blank=True)

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        db_table = "recipient_reported_issue"
        indexes = [models.Index(fields=["job", "created_at"], name="ix_recipient_issue_job")]


class HighValueApproval(AppendOnlyModel):
    job = models.OneToOneField(Job, on_delete=models.PROTECT, related_name="high_value_approval")
    requested_at = models.DateTimeField(auto_now_add=True)
    decided_by_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    decided_by_is_platform_admin = models.BooleanField(default=False)
    decision = models.CharField(max_length=12, choices=HighValueDecision.choices)
    rationale = models.TextField(blank=True, default="")

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        db_table = "high_value_approval"


class JobTransitionIdempotency(models.Model):
    """Stored response for an ``Idempotency-Key`` on a lifecycle transition
    (job-state-machine.md §2.1 step 1 & 12). Scoped ``(actor_key, job, key)``;
    a replay returns ``stored_response`` verbatim with no second side effect.

    This is a DB row (not the HTTP-layer cache in ``common.idempotency``) so a
    scheduled sweep or an event-handler retry is idempotent too, not only an
    HTTP client replay. Pruned after 24h by a later sweep (plan §19 Step 11)."""

    actor_key = models.CharField(max_length=64)
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="+")
    idempotency_key = models.CharField(max_length=200)
    stored_response = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "job_transition_idempotency"
        constraints = [
            models.UniqueConstraint(
                fields=["actor_key", "job", "idempotency_key"],
                name="uq_job_transition_idempotency",
            ),
        ]


class AllowedJobTransition(models.Model):
    """Seed table backing the ``BEFORE UPDATE OF status ON job`` trigger (ADR-2D-03).
    Populated in the 0002 migration from ``jobs.transitions.ALLOWED_TRANSITIONS``."""

    from_status = models.CharField(max_length=16)
    to_status = models.CharField(max_length=16)

    class Meta:
        db_table = "allowed_job_transition"
        constraints = [
            models.UniqueConstraint(
                fields=["from_status", "to_status"], name="uq_allowed_job_transition"
            )
        ]


def money_str(minor_units: int | None) -> str:  # pragma: no cover - helper
    if minor_units is None:
        return "—"
    return f"KSh {minor_units / 100:,.2f}"


__all__: list[str] = [name for name in dir() if name[0].isupper()]
_ = Any  # keep the import referenced for type-checkers in stubs
