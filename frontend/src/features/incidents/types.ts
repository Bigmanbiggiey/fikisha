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

// ─── Write shapes ──────────────────────────────────────────────────────
export interface ReportIncidentBody {
  type: IncidentType;
  severity?: IncidentSeverity;
  description?: string;
  other_label?: string;
}

export interface ResolveDisputeBody {
  outcome_code: ResolutionOutcome;
  rationale: string;
  routed_job_status: RoutableJobStatus;
  commission_treatment?: CommissionTreatment;
  reduced_amount_kes?: number;
  agreed_compensation_kes?: number;
}
