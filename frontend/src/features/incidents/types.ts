/**
 * Field names/shapes taken directly from the backend's actual projections —
 * `fikisha.incidents.api.views._incident_view()` / `_dispute_view()` — not
 * re-guessed. See `docs/phase-2/phase-2d-api.md` §4. `evidence`/`statements`
 * were added to `_incident_view()` alongside this file (Design Phase 6
 * Increment 7 — previously POST-only, unreadable).
 */

export const INCIDENT_TYPES = [
  'DAMAGE',
  'LOSS',
  'MISSING_GOODS',
  'WRONG_RECIPIENT',
  'WRONG_PICKUP',
  'MISCONDUCT',
  'BREAKDOWN',
  'ACCIDENT',
  'DELAY',
  'CANCELLATION',
  'NON_PAYMENT',
  'OTHER',
] as const;
export type IncidentType = (typeof INCIDENT_TYPES)[number];

export const INCIDENT_SEVERITIES = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'] as const;
export type IncidentSeverity = (typeof INCIDENT_SEVERITIES)[number];

/** Shared by `Incident.status` and `Dispute.status` — the backend uses the
 * identical 5-value enum for both. */
export const INCIDENT_STATUSES = [
  'OPEN',
  'UNDER_REVIEW',
  'AMICABLE_PENDING',
  'RESOLVED',
  'ESCALATED',
] as const;
export type IncidentStatus = (typeof INCIDENT_STATUSES)[number];
export type DisputeStatus = IncidentStatus;

export const RESOLUTION_OUTCOMES = [
  'AMICABLE_AGREEMENT',
  'ADMIN_DETERMINATION',
  'WITHDRAWN',
] as const;
export type ResolutionOutcome = (typeof RESOLUTION_OUTCOMES)[number];

export const COMMISSION_TREATMENTS = ['APPLY', 'REDUCE', 'WAIVE'] as const;
export type CommissionTreatment = (typeof COMMISSION_TREATMENTS)[number];

/** `DISPUTED → RESUME` is not implemented (ADR-2D-07, O-P1) — these are the
 * only statuses a resolution may ever route to. A DB `CHECK` constraint
 * enforces this server-side; nothing here should ever offer a 4th option. */
export const ROUTABLE_JOB_STATUSES = ['CANCELLED', 'COMPLETED', 'FAILED'] as const;
export type RoutableJobStatus = (typeof ROUTABLE_JOB_STATUSES)[number];

export interface IncidentEvidenceItem {
  id: string;
  evidence_object_id: string;
  caption: string;
  uploaded_by_kind: string;
  created_at: string;
}

export interface IncidentStatementItem {
  id: string;
  party_kind: string;
  text: string;
  created_at: string;
}

/** Reasons staff may choose when closing an incident by hand
 * (`MANUAL_CLOSURE_REASONS`); `DISPUTE_RESOLVED` is written only by
 * resolving a dispute. */
export const MANUAL_CLOSURE_REASONS = [
  'RESOLVED_BETWEEN_PARTIES',
  'PAYMENT_MADE',
  'WITHDRAWN',
  'NO_ACTION_NEEDED',
  'OTHER',
] as const;
export type ClosureReason = (typeof MANUAL_CLOSURE_REASONS)[number] | 'DISPUTE_RESOLVED';

export interface IncidentClosure {
  reason_code: ClosureReason;
  created_at: string;
  /** staff only */
  note?: string;
}

export const FINDING_OUTCOMES = ['AT_FAULT', 'NO_FAULT', 'UNDETERMINED'] as const;
export type FindingOutcome = (typeof FINDING_OUTCOMES)[number];
export type FindingPartyKind = 'BUSINESS' | 'DRIVER' | 'GROUP';

/** Fikisha's finding (trust plan A2). `reason` and the rest are staff-only. */
export interface IncidentFinding {
  id: string;
  outcome: FindingOutcome;
  parties: FindingPartyKind[];
  created_at: string;
  reason?: string;
  decided_by_is_platform_admin?: boolean;
  supersedes_id?: string | null;
}

export interface Incident {
  id: string;
  job_id: string;
  type: IncidentType;
  other_label: string;
  severity: IncidentSeverity | '';
  status: IncidentStatus;
  description: string;
  reported_by_kind: string;
  created_at: string;
  sla_ack_due_at: string | null;
  sla_action_due_at: string | null;
  sla_resolution_due_at: string | null;
  evidence: IncidentEvidenceItem[];
  statements: IncidentStatementItem[];
  closure: IncidentClosure | null;
  finding: IncidentFinding | null;
  /** staff only */
  finding_history?: IncidentFinding[];
  finding_candidates?: FindingPartyKind[];
  unfounded?: { reason: string; created_at: string } | null;
}

export interface Resolution {
  id: string;
  outcome_code: ResolutionOutcome;
  rationale: string;
  routed_job_status: RoutableJobStatus;
  /** the operator side's commission */
  commission_treatment: CommissionTreatment;
  /** the business side's commission (commission split D-5) */
  business_commission_treatment?: CommissionTreatment;
  /** intent flags recorded before findings existed; history only */
  recorded_actions?: string[];
  /** resolved by resuming the job to `routed_job_status` (trust plan B1) */
  resumed?: boolean;
  created_at: string;
}

export interface Dispute {
  id: string;
  job_id: string;
  incident_ids: string[];
  status: DisputeStatus;
  pre_dispute_status: string;
  created_at: string;
  resolution: Resolution | null;
}

// ─── Write shapes ──────────────────────────────────────────────────────
export interface ReportIncidentBody {
  type: IncidentType;
  severity?: IncidentSeverity;
  description?: string;
  other_label?: string;
}

export interface CloseIncidentBody {
  reason_code: ClosureReason;
  note: string;
}

export interface RecordFindingBody {
  outcome: FindingOutcome;
  parties: FindingPartyKind[];
  reason: string;
}

export const AGREEMENT_METHODS = ['PHONE', 'IN_PERSON', 'IN_APP_MESSAGE'] as const;
export type AgreementMethod = (typeof AGREEMENT_METHODS)[number];

/** `GET /disputes/:id/resume` (trust plan B1). */
export interface ResumeChecks {
  target_status: string;
  window_ends_at: string;
  checks: { key: string; ok: boolean; detail: string }[];
  ok: boolean;
}

export interface ResumeDisputeBody {
  sender_method: AgreementMethod;
  operator_method: AgreementMethod;
  reason: string;
}

export interface ResolveDisputeBody {
  outcome_code: ResolutionOutcome;
  rationale: string;
  routed_job_status: RoutableJobStatus;
  /** the operator side's commission */
  commission_treatment?: CommissionTreatment;
  reduced_amount_kes?: number;
  /** the business side's (commission split D-5); left out, the same as the
   * operator side's treatment and amount */
  business_commission_treatment?: CommissionTreatment;
  business_reduced_amount_kes?: number;
  agreed_compensation_kes?: number;
}
