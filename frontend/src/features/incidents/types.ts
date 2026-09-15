/** Field names/shapes taken directly from `fikisha.incidents.api.views._incident_view()`
 * / `_dispute_view()` and `api/serializers.py` — see `docs/phase-2/phase-2d-api.md` §4.
 * The 11-value taxonomy is verbatim from FR-D-1 (`incidents/constants.py`) — do not
 * add categories casually. */

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
  'OTHER',
] as const;
export type IncidentType = (typeof INCIDENT_TYPES)[number];

export const INCIDENT_SEVERITIES = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'] as const;
export type IncidentSeverity = (typeof INCIDENT_SEVERITIES)[number];

export const INCIDENT_STATUSES = [
  'OPEN',
  'UNDER_REVIEW',
  'AMICABLE_PENDING',
  'RESOLVED',
  'ESCALATED',
] as const;
export type IncidentStatus = (typeof INCIDENT_STATUSES)[number];

export const REPORTED_BY_KINDS = ['USER', 'RECIPIENT_LINK', 'ADMIN'] as const;
export type ReportedByKind = (typeof REPORTED_BY_KINDS)[number];

/** Mirrors IncidentStatus — a Dispute is its own small workflow, independent
 * of `Job.status` (which only ever reads DISPUTED for the whole window). */
export const DISPUTE_STATUSES = INCIDENT_STATUSES;
export type DisputeStatus = IncidentStatus;

export const RESOLUTION_OUTCOMES = [
  'AMICABLE_AGREEMENT',
  'ADMIN_DETERMINATION',
  'WITHDRAWN',
] as const;
export type ResolutionOutcome = (typeof RESOLUTION_OUTCOMES)[number];

export const COMMISSION_TREATMENTS = ['APPLY', 'REDUCE', 'WAIVE'] as const;
export type CommissionTreatment = (typeof COMMISSION_TREATMENTS)[number];

/** Recorded intents only — nothing executes these (ADR-2D-21). No rating/
 * trust/suspension engine exists; do not build UI implying one does. */
export const RESOLUTION_ACTIONS = ['NONE', 'RATING_IMPACT', 'TRUST_CHANGE', 'SUSPENSION'] as const;
export type ResolutionAction = (typeof RESOLUTION_ACTIONS)[number];

/** `DISPUTED -> RESUME` is not one of these — it's not implemented (E-1,
 * ADR-2D-07). A resolution may only route to one of these three. */
export const ROUTABLE_JOB_STATUSES = ['CANCELLED', 'COMPLETED', 'FAILED'] as const;
export type RoutableJobStatus = (typeof ROUTABLE_JOB_STATUSES)[number];

export interface Incident {
  id: string;
  job_id: string;
  type: IncidentType;
  other_label: string;
  severity: IncidentSeverity;
  status: IncidentStatus;
  description: string;
  reported_by_kind: ReportedByKind;
  created_at: string;
  sla_ack_due_at: string | null;
  sla_action_due_at: string | null;
  sla_resolution_due_at: string | null;
}

export interface Resolution {
  id: string;
  outcome_code: ResolutionOutcome;
  rationale: string;
  routed_job_status: RoutableJobStatus;
  commission_treatment: CommissionTreatment;
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

export interface Escalation {
  id: string;
  incident_id: string;
  dispute_id: string | null;
  escalated_to: string;
}

export interface EvidenceAttachResult {
  id: string;
  evidence_object_id: string;
}

export interface Statement {
  id: string;
  party_kind: string;
  text: string;
  created_at: string;
}

// ─── request bodies ────────────────────────────────────────────────────
export interface ReportIncidentBody {
  type: IncidentType;
  severity?: IncidentSeverity;
  description?: string;
  other_label?: string;
}

export interface AttachEvidenceBody {
  file: File;
  caption?: string;
}

export interface AddStatementBody {
  text: string;
}

export interface EscalateBody {
  reason: string;
  escalated_to?: string;
  advised_external_options?: boolean;
}

export interface OpenDisputeBody {
  incident_ids: string[];
}

export interface ResolveDisputeBody {
  outcome_code: ResolutionOutcome;
  rationale: string;
  routed_job_status: RoutableJobStatus;
  commission_treatment?: CommissionTreatment;
  reduced_amount_kes?: number;
  agreed_compensation_kes?: number;
  actions?: ResolutionAction[];
}
