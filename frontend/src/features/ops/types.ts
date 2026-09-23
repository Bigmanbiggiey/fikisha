/**
 * Ops console shapes (Design Phase 6 Increment 8) — taken directly from the
 * backend projections: `fikisha.jobs.ops` (`ops_rows` / `high_value_rows` /
 * `_note_view` / `events_for` / `reveal_contacts`), the incidents
 * `_IncidentQueueRow` / `_DisputeQueueRow`, and `audit.api._AuditEntryRow`.
 * See `docs/phase-2/phase-2d-api.md`.
 */
import type { JobStatus, ValueBand } from '@/features/jobs/types';

export type AttentionFilter = 'disputed' | 'failed' | 'high_value_pending' | 'stale';

export interface MonitorFilters {
  status?: JobStatus[];
  value_band?: ValueBand;
  ref?: string;
  attention?: AttentionFilter;
  stale_hours?: number;
}

export interface OpsJobRow {
  id: string;
  reference: string;
  status: JobStatus;
  value_band: ValueBand | null;
  is_high_value: boolean;
  business_name: string;
  pickup_area: string;
  destination_area: string;
  created_at: string;
  last_changed_at: string;
}

export interface HighValueRow extends OpsJobRow {
  declared_value_kes: number;
  needs_platform_admin: boolean;
  operator_name: string | null;
}

export type HighValueDecision = 'APPROVED' | 'REJECTED';

export interface JobNote {
  id: string;
  text: string;
  created_at: string;
  author_label: string;
  /** Staff-only fields — absent for a job party. */
  author_role?: string;
  author_user_id?: string | null;
}

export interface JobEventRow {
  seq: number;
  category: string;
  type: string;
  is_custody: boolean;
  actor_role: string;
  from_status: JobStatus | null;
  to_status: JobStatus | null;
  server_time: string;
  confirmation_method: string | null;
  geo_state: string;
  evidence_count: number;
  note: string;
}

export interface PartyContact {
  name: string;
  phone: string;
}

export type ContactParty = 'business' | 'pickup' | 'destination' | 'recipient' | 'operator' | 'driver';

export interface RevealedContacts {
  job_id: string;
  contacts: Record<ContactParty, PartyContact | null>;
}

export interface IncidentQueueRow {
  id: string;
  job_id: string;
  job_reference: string;
  type: string;
  other_label: string;
  severity: string;
  status: string;
  created_at: string;
  sla_ack_due_at: string | null;
}

export interface DisputeQueueRow {
  id: string;
  job_id: string;
  job_reference: string;
  status: string;
  value_band: ValueBand;
  needs_platform_admin: boolean;
  created_at: string;
}

export interface AuditFilters {
  actor_user?: string;
  entity_type?: string;
  entity_id?: string;
  action?: string;
  from?: string;
  to?: string;
}

export interface AuditEntryRow {
  seq: number;
  server_time: string;
  actor_user_id: string | null;
  actor_role: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  before: unknown;
  after: unknown;
  source_channel: string;
}
