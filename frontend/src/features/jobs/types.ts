/**
 * Field names and shapes here are taken directly from the backend's actual
 * projections — `fikisha.jobs.dto.job_view()` / `creation.job_detail()` for
 * `Job`/`JobTransitionResult`, `api/serializers.py` for the write shapes —
 * not re-guessed. See `docs/phase-2/phase-2d-api.md`.
 *
 * Every `*_kes` field is an integer in KES **minor units** (cents) —
 * `fikisha.common.money.Money`, `CLAUDE.md` §4. Use `money.ts`'s
 * `formatKes()`/`parseKesToMinorUnits()`, never display or parse these raw.
 */

export type Paged<T> = { data: T[]; page: { next_cursor: string | null; prev_cursor: string | null } };

/** The 14 approved Job states (`CLAUDE.md` §4) — exact set, never re-mapped. */
export const JOB_STATUSES = [
  'DRAFT',
  'REQUESTED',
  'NEGOTIATING',
  'CONFIRMED',
  'ASSIGNED',
  'AT_PICKUP',
  'PICKED_UP',
  'IN_TRANSIT',
  'AT_DESTINATION',
  'DELIVERED',
  'COMPLETED',
  'CANCELLED',
  'FAILED',
  'DISPUTED',
] as const;
export type JobStatus = (typeof JOB_STATUSES)[number];

export const VALUE_BANDS = ['STANDARD', 'ELEVATED', 'HIGH', 'VERY_HIGH'] as const;
export type ValueBand = (typeof VALUE_BANDS)[number];

export const CANCELLATION_REASONS = [
  'BUSINESS_CHANGED_MIND',
  'OPERATOR_UNAVAILABLE',
  'NO_ACCEPTABLE_OFFER',
  'PRICE_DISAGREEMENT',
  'ADMIN_ACTION',
  'OTHER',
] as const;
export type CancellationReason = (typeof CANCELLATION_REASONS)[number];

export interface JobLocation {
  id: string;
  type: 'PICKUP' | 'DESTINATION';
  address_text: string;
  lat: string | null;
  lng: string | null;
  contact_name: string;
  contact_phone: string;
}

export interface JobCargo {
  id: string;
  description: string;
  declared_value_kes: number;
  handling_flags: string[];
}

export interface JobTimestamps {
  created_at: string | null;
  published_at: string | null;
  confirmed_at: string | null;
  assigned_at: string | null;
  picked_up_at: string | null;
  delivered_at: string | null;
  completed_at: string | null;
  terminal_at: string | null;
}

/** Returned by submit/cancel/assign/every custody transition — `job_view()`. */
export interface JobTransitionResult {
  id: string;
  status: JobStatus;
  version: number;
  business_id: string;
  created_by_id: string;
  value_band: ValueBand;
  required_trust_level: number;
  is_high_value: boolean;
  latent_risk_cargo: boolean;
  declared_value_kes: number;
  proposed_price_kes: number | null;
  agreement_id: string | null;
  assignment_id: string | null;
  config_version_id: string | null;
  is_terminal: boolean;
  next_allowed_statuses: JobStatus[];
  timestamps: JobTimestamps;
}

/** Returned by list/detail/create — `job_detail()`, a superset of the above. */
export interface Job extends JobTransitionResult {
  pickup_location: JobLocation | null;
  destination_location: JobLocation | null;
  recipient_name: string;
  recipient_phone: string;
  cargo: JobCargo | null;
  agreed_price_kes: number | null;
  assigned_driver_id: string | null;
  assigned_vehicle_id: string | null;
}

// ─── Create-Job request shape (JobCreateSerializer) ───────────────────────
export interface LocationWrite {
  address_text?: string;
  lat?: number | null;
  lng?: number | null;
  contact_name?: string;
  contact_phone?: string;
  notes?: string;
}

export interface CargoWrite {
  description: string;
  category_code?: string;
  est_weight_kg?: number | null;
  dims_l_cm?: number | null;
  dims_w_cm?: number | null;
  dims_h_cm?: number | null;
  declared_value_kes: number;
  handling_flags?: string[];
}

export interface VehicleRequirementWrite {
  required_vehicle_class_codes?: string[];
  min_payload_kg?: number;
  min_volume_m3?: number | null;
  required_features?: string[];
  notes?: string;
}

export interface JobCreateBody {
  pickup_location: LocationWrite;
  destination_location: LocationWrite;
  cargo: CargoWrite;
  vehicle_requirement?: VehicleRequirementWrite;
  recipient_name?: string;
  recipient_phone?: string;
  delivery_requirements?: string;
  delivery_flags?: string[];
  proposed_price_kes?: number | null;
  latent_risk_cargo?: boolean;
}

// ─── Custody / assignment request shapes ──────────────────────────────────
export interface GeoBody {
  lat?: number | null;
  lng?: number | null;
  accuracy_m?: number | null;
}

export interface AssignBody {
  driver_profile_id: string;
  vehicle_id: string;
  admin_override_reason?: string;
}

// ─── Work discovery / assignment candidates (Design Phase 6 Increment 4) ──
// Individual-operator-only this increment — see
// `backend/fikisha/jobs/discovery.py` / `jobs/assignment_candidates.py`.
export interface JobEligibility {
  eligible: boolean;
  trust_level: string;
  reasons: string[];
}

/** `job_detail()` plus a per-job eligibility marker for the viewing operator
 * — `GET /jobs/opportunities`. */
export interface Opportunity extends Job {
  eligibility: JobEligibility;
}

export interface DriverCandidate {
  id: string;
  name: string;
  trust_level: string;
  eligible: boolean;
  reasons: string[];
}

export interface VehicleCandidate {
  id: string;
  registration: string;
  vehicle_class: string | null;
  capacity_value: string;
  capacity_unit: string;
  status: string;
  eligible: boolean;
  reasons: string[];
}

export interface AssignmentCandidates {
  job_id: string;
  value_band: ValueBand;
  /** Always `false` this increment — Group Manager assign is deferred. */
  supports_group_assignment: boolean;
  /** Non-null when a HIGH/VERY_HIGH pre-assignment review is still pending. */
  blocked: string | null;
  drivers: DriverCandidate[];
  vehicles: VehicleCandidate[];
}

export interface DiscoveryFilters {
  value_band?: ValueBand;
}

export interface ConfirmPickupOtpBody extends GeoBody {
  code: string;
  condition_note?: string;
}

export interface ConfirmPickupBusinessBody extends GeoBody {
  condition_note?: string;
}

export interface ConfirmPickupAttestedBody extends GeoBody {
  pickup_contact_name: string;
  condition_note?: string;
}

export interface FailAtPickupBody {
  reason_text: string;
}

export interface ConfirmDeliveryBody extends GeoBody {
  party_name: string;
  code?: string;
  condition_note?: string;
}

// ─── Commission read ───────────────────────────────────────────────────────
export interface CommissionAdjustment {
  id: string;
  kind: string;
  amount_kes: number;
  reason: string;
  created_at: string;
}

export interface CommissionView {
  job_id: string;
  commission_kes: number;
  rate: string;
  min_fee_kes: number;
  cap_kes: number;
  agreed_price_kes: number;
  currency: string;
  effective_commission_kes: number;
  adjustments: CommissionAdjustment[];
}

// ─── Recipient scoped access (no bearer auth — token in the URL) ─────────
export interface RecipientView {
  delivery_reference: string;
  recipient_display_name: string;
  cargo_summary: string;
  status: JobStatus;
  status_label: string;
  driver_first_name: string;
  vehicle_class: string;
  vehicle_plate: string;
  operator_identity_verified: boolean;
  allowed_actions: string[];
}

export const RECIPIENT_ISSUE_CATEGORIES = [
  'WRONG_RECIPIENT',
  'DAMAGE',
  'MISSING_GOODS',
  'WRONG_GOODS',
  'OTHER',
] as const;
export type RecipientIssueCategory = (typeof RECIPIENT_ISSUE_CATEGORIES)[number];

export interface RecipientConfirmBody {
  code: string;
  party_name: string;
}

export interface RecipientReportIssueBody {
  category: RecipientIssueCategory;
  description?: string;
  other_label?: string;
}
