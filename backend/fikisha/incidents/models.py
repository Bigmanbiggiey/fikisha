"""Incidents & Disputes data model (database-design.md §4.10, dispute-and-
liability.md, FR-D-1..D-10).

Deliberately separate from the Job lifecycle: an ``Incident`` never writes
``job.status``; only ``Dispute``-opening/resolution — via
``JobLifecycleService.transition()``, never directly — does, and only along
the rows already in the approved ``ALLOWED_TRANSITIONS`` table.

ADR-2D-20: ``Dispute.job`` is a plain FK with a **partial** unique constraint
(`at most one non-RESOLVED dispute per job`), not the hard `U(job_id)` database-
design.md §4.10 states literally. A job can be legitimately disputed more than
once across its lifetime — e.g. a custody dispute resolved to COMPLETED, then a
later, separate post-completion dispute opens within the window — which the
already-approved `COMPLETED → DISPUTED` transition permits. A hard one-row-
per-job-ever constraint would silently break that approved path. The predicate
is on ``status`` (static data), never on `now()` / current time, so this does
not touch the Increment-5 "no `now()` in a partial index" rule.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from fikisha.common.models import AppendOnlyModel, AppendOnlyQuerySet, TimestampedModel
from fikisha.incidents.constants import (
    RESUMABLE_STATUSES,
    ROUTABLE_JOB_STATUSES,
    AgreementMethod,
    ClosureReason,
    CommissionTreatment,
    DisputeStatus,
    FindingOutcome,
    FindingPartyKind,
    IncidentSeverity,
    IncidentStatus,
    IncidentType,
    PartyKind,
    ReportedByKind,
    ResolutionOutcome,
)
from fikisha.jobs.constants import JobStatus

_OPEN_DISPUTE_STATUSES = [
    DisputeStatus.OPEN,
    DisputeStatus.UNDER_REVIEW,
    DisputeStatus.AMICABLE_PENDING,
    DisputeStatus.ESCALATED,
]


class Incident(TimestampedModel):
    """Operational/problem record. Does **not** by itself move ``job.status`` —
    only a ``Dispute`` opened against a progression-blocking incident does
    (FR-D-3), via the Job Lifecycle Service."""

    job = models.ForeignKey("jobs.Job", on_delete=models.PROTECT, related_name="incidents")
    type = models.CharField(max_length=20, choices=IncidentType.choices)
    other_label = models.CharField(max_length=120, blank=True, default="")
    severity = models.CharField(max_length=8, choices=IncidentSeverity.choices)
    reported_by_kind = models.CharField(max_length=16, choices=ReportedByKind.choices)
    reported_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    # Plain UUID, not a FK: a recipient access link can be revoked/replaced
    # (Increment 5's amended lifecycle deletes superseded rows) — same
    # append-only-survives-the-link-lifecycle reasoning as
    # RecipientReportedIssue.reported_via_link_id.
    reported_by_link_id = models.UUIDField(null=True, blank=True)
    #: The reporter's side of the job when they reported it (BUSINESS /
    #: OPERATOR / GROUP / RECIPIENT / ADMIN), fixed at creation so later
    #: membership changes never re-attribute it. Blank on incidents reported
    #: before it existed (trust-and-disputes plan A5).
    reporter_party = models.CharField(
        max_length=16, choices=PartyKind.choices, blank=True, default=""
    )
    # The originating recipient report, if this incident was intake'd from one
    # (plan §19 Step 8 brief §7) — never mutated, only referenced.
    source_report_id = models.UUIDField(null=True, blank=True)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=16, choices=IncidentStatus.choices, default=IncidentStatus.OPEN
    )
    owner_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    #: Who made the latest change to this record (created it, or moved its
    #: status); null for a recipient-link report. The Messages inbox uses it
    #: to tell activity the viewer wrote from activity they haven't seen
    #: (PR #5 follow-up 4; replaces an "updated within 2 s of creation" guess).
    last_changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    linked_custody_event_ids = models.JSONField(default=list, blank=True)
    # SLA targets (config-driven, platform_config.sla_targets — already
    # approved/present) computed once at creation; informational only in
    # Step 8, no enforcement sweep.
    sla_ack_due_at = models.DateTimeField(null=True, blank=True)
    sla_action_due_at = models.DateTimeField(null=True, blank=True)
    sla_resolution_due_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "incident"
        indexes = [
            models.Index(fields=["job", "status"], name="ix_incident_job_status"),
            models.Index(
                fields=["status"],
                name="ix_incident_open",
                condition=models.Q(status__in=["OPEN", "UNDER_REVIEW", "AMICABLE_PENDING"]),
            ),
        ]

    def __str__(self) -> str:  # pragma: no cover - debug aid
        return f"Incident {self.pk} [{self.type}/{self.status}] on job {self.job_id}"

    @property
    def is_blocking_eligible(self) -> bool:
        """Not yet resolved — the only state a freeze may reference."""
        return self.status != IncidentStatus.RESOLVED


class IncidentEvidence(AppendOnlyModel):
    incident = models.ForeignKey(Incident, on_delete=models.PROTECT, related_name="evidence")
    evidence_object = models.ForeignKey(
        "evidence.EvidenceObject", on_delete=models.PROTECT, related_name="+"
    )
    uploaded_by_kind = models.CharField(max_length=16, choices=PartyKind.choices)
    uploaded_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    caption = models.CharField(max_length=200, blank=True, default="")

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        db_table = "incident_evidence"
        indexes = [models.Index(fields=["incident", "created_at"])]


class IncidentStatement(AppendOnlyModel):
    """Append-only. A correction is a new statement, not an edit (FR-D-4)."""

    incident = models.ForeignKey(Incident, on_delete=models.PROTECT, related_name="statements")
    party_kind = models.CharField(max_length=16, choices=PartyKind.choices)
    party_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    text = models.TextField()

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        db_table = "incident_statement"
        ordering = ["created_at"]
        indexes = [models.Index(fields=["incident", "created_at"])]


class IncidentClosure(AppendOnlyModel):
    """Why and by whom an incident was closed (trust-and-disputes plan A1).
    One per incident, append-only. Says nothing about fault."""

    incident = models.OneToOneField(Incident, on_delete=models.PROTECT, related_name="closure")
    reason_code = models.CharField(max_length=32, choices=ClosureReason.choices)
    note = models.TextField()
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    closed_by_is_platform_admin = models.BooleanField(default=False)
    #: Set when the closure came from resolving this dispute.
    dispute = models.ForeignKey(
        "Dispute", null=True, blank=True, on_delete=models.PROTECT, related_name="closures"
    )

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        db_table = "incident_closure"


class IncidentFinding(AppendOnlyModel):
    """Fikisha's finding on an incident (trust-and-disputes plan A2).
    Append-only; a correction is a new row that ``supersedes`` the current
    one. The current finding is the one nothing supersedes: the database
    allows one first finding per incident and each finding to be superseded
    once, so there is exactly one current finding per incident."""

    incident = models.ForeignKey(Incident, on_delete=models.PROTECT, related_name="findings")
    outcome = models.CharField(max_length=16, choices=FindingOutcome.choices)
    reason = models.TextField()
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    decided_by_is_platform_admin = models.BooleanField(default=False)
    supersedes = models.OneToOneField(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="superseded_by"
    )

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        db_table = "incident_finding"
        constraints = [
            models.UniqueConstraint(
                fields=["incident"],
                condition=models.Q(supersedes__isnull=True),
                name="uq_incident_finding_one_first",
            ),
        ]
        indexes = [models.Index(fields=["incident", "created_at"])]


class IncidentFindingParty(AppendOnlyModel):
    """A party an AT_FAULT finding names. ``subject_id`` is the business,
    the driver's operator profile, or the group, derived from the job."""

    finding = models.ForeignKey(IncidentFinding, on_delete=models.PROTECT, related_name="parties")
    kind = models.CharField(max_length=10, choices=FindingPartyKind.choices)
    subject_id = models.UUIDField()

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        db_table = "incident_finding_party"
        constraints = [
            models.UniqueConstraint(fields=["finding", "kind"], name="uq_finding_party_kind"),
        ]
        indexes = [models.Index(fields=["kind", "subject_id"], name="ix_finding_party_subject")]


class UnfoundedReport(AppendOnlyModel):
    """A Platform Admin's record that a report was unfounded (plan A3, UF-1),
    against the reporter. Only on a closed incident whose current finding is
    NO_FAULT. No automatic effect."""

    incident = models.OneToOneField(
        Incident, on_delete=models.PROTECT, related_name="unfounded_report"
    )
    finding = models.ForeignKey(IncidentFinding, on_delete=models.PROTECT, related_name="+")
    reporter_party = models.CharField(max_length=16, choices=PartyKind.choices, blank=True)
    reporter_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    reporter_link_id = models.UUIDField(null=True, blank=True)
    reason = models.TextField()
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        db_table = "unfounded_report"


class Dispute(TimestampedModel):
    """One row per dispute **episode**; a job may have more than one across its
    lifetime (ADR-2D-20). ``pre_dispute_status`` is stamped by
    ``incidents.services.open_dispute()`` from the same **locked** job row the
    transition itself then reads (job-state-machine.md §5.1) — not implied to
    be resumable (E-1 stays OPEN; RESUME is not implemented)."""

    job = models.ForeignKey("jobs.Job", on_delete=models.PROTECT, related_name="disputes")
    incident_ids = models.JSONField(default=list, blank=True)
    opened_by_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    status = models.CharField(
        max_length=16, choices=DisputeStatus.choices, default=DisputeStatus.OPEN
    )
    officer_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    pre_dispute_status = models.CharField(max_length=16, choices=JobStatus.choices)

    class Meta:
        db_table = "dispute"
        constraints = [
            models.UniqueConstraint(
                fields=["job"],
                condition=models.Q(status__in=_OPEN_DISPUTE_STATUSES),
                name="uq_dispute_one_open_per_job",
            ),
        ]
        indexes = [models.Index(fields=["job", "status"], name="ix_dispute_job_status")]

    def __str__(self) -> str:  # pragma: no cover - debug aid
        return f"Dispute {self.pk} on job {self.job_id} [{self.status}]"


class Resolution(AppendOnlyModel):
    """One per dispute, append-only, immutable once written (FR-D-6/D-7). The
    financial-adjustment **boundary** for Step 8 (brief §14): records the
    decision (``commission_treatment`` / ``reduced_amount_kes`` /
    ``agreed_compensation_kes``) without itself touching any commission
    ledger row. Step 9 built the ledger (``jobs.CommissionRecord`` /
    ``CommissionAdjustment``) and reads these fields from
    ``incidents.services.resolve_dispute()`` to create an adjustment when
    ``commission_treatment`` is ``REDUCE``/``WAIVE`` — this row itself is
    still just the recorded decision, never mutated afterward.
    ``agreed_compensation_kes`` is deliberately never wired to commission (it
    is party-to-party compensation intent; Fikisha still never holds the
    transport fare). ``actions`` are recorded intents only; Step 8 executes
    none of them (ADR-2D-21)."""

    dispute = models.OneToOneField(Dispute, on_delete=models.PROTECT, related_name="resolution")
    outcome_code = models.CharField(max_length=20, choices=ResolutionOutcome.choices)
    rationale = models.TextField()
    commission_treatment = models.CharField(
        max_length=8, choices=CommissionTreatment.choices, default=CommissionTreatment.APPLY
    )
    reduced_amount_kes = models.BigIntegerField(null=True, blank=True)
    agreed_compensation_kes = models.BigIntegerField(null=True, blank=True)
    actions = models.JSONField(default=list, blank=True)
    routed_job_status = models.CharField(max_length=16, choices=JobStatus.choices)
    resolved_by_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    resolved_by_is_platform_admin = models.BooleanField(default=False)
    #: The dispute was resolved by resuming the job to ``routed_job_status``,
    #: its recorded pre-dispute state (trust-and-disputes plan B1).
    resumed = models.BooleanField(default=False)

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        db_table = "resolution"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(resumed=False, routed_job_status__in=list(ROUTABLE_JOB_STATUSES))
                    | models.Q(resumed=True, routed_job_status__in=list(RESUMABLE_STATUSES))
                ),
                name="ck_resolution_routed_status",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(reduced_amount_kes__isnull=True) | models.Q(reduced_amount_kes__gte=0)
                ),
                name="ck_resolution_reduced_amount_non_negative",
            ),
        ]

    def __str__(self) -> str:  # pragma: no cover - debug aid
        return f"Resolution for dispute {self.dispute_id} -> {self.routed_job_status}"


class Escalation(AppendOnlyModel):
    """FR-D-8: critical incidents / unresolved disputes may be escalated (e.g.
    to the founder); the platform records that parties were advised of
    external options. It does not adjudicate criminal matters."""

    incident = models.ForeignKey(Incident, on_delete=models.PROTECT, related_name="escalations")
    dispute = models.ForeignKey(
        Dispute, null=True, blank=True, on_delete=models.PROTECT, related_name="escalations"
    )
    reason = models.TextField()
    escalated_to = models.CharField(max_length=120)
    advised_external_options = models.BooleanField(default=False)

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        db_table = "escalation"


class ResumeAttestation(AppendOnlyModel):
    """The Platform Admin's record that both parties agreed the job should
    carry on (trust-and-disputes plan DR-1): how each was confirmed and when,
    if known. No transcripts or phone numbers."""

    dispute = models.OneToOneField(Dispute, on_delete=models.PROTECT, related_name="resume")
    resolution = models.OneToOneField(Resolution, on_delete=models.PROTECT, related_name="+")
    sender_method = models.CharField(max_length=16, choices=AgreementMethod.choices)
    sender_confirmed_at = models.DateTimeField(null=True, blank=True)
    operator_method = models.CharField(max_length=16, choices=AgreementMethod.choices)
    operator_confirmed_at = models.DateTimeField(null=True, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        db_table = "resume_attestation"
