import type { Paged } from '@/features/jobs/types';

/** Directory kinds, as the API names them (`/admin/directory/<kind>`). */
export type DirectoryKind = 'businesses' | 'operators' | 'groups';
export type AccountType = 'USER' | 'OPERATOR' | 'BUSINESS' | 'GROUP';
export type InterventionAction = 'SUSPEND' | 'REINSTATE' | 'OFFBOARD';

export const KIND_TO_ACCOUNT: Record<DirectoryKind, AccountType> = {
  businesses: 'BUSINESS',
  operators: 'OPERATOR',
  groups: 'GROUP',
};

/** The states each directory can be filtered by (server enums). */
export const KIND_STATES: Record<DirectoryKind, string[]> = {
  businesses: ['GOOD', 'RESTRICTED', 'SUSPENDED'],
  operators: ['PENDING', 'ACTIVE', 'RESTRICTED', 'SUSPENDED', 'OFFBOARDED'],
  groups: ['GOOD', 'RESTRICTED', 'SUSPENDED'],
};

export interface DirectoryRow {
  id: string;
  kind: AccountType;
  name: string;
  /** standing (business, group) or status (operator) */
  state: string;
  /** masked, e.g. "+2547•••••678"; the full number needs a reveal */
  phone: string | null;
  verification_status?: string;
  member_count?: number | null;
  category?: string;
  full_name?: string;
  group_type?: string;
  assignment_mode?: string;
  created_at: string;
}

export interface Intervention {
  id: string;
  action: InterventionAction;
  reason: string;
  duration_days: number | null;
  before_state: string;
  after_state: string;
  admin_name: string;
  created_at: string;
}

export interface DirectoryMember {
  user_id?: string;
  operator_id?: string;
  name: string;
  role: string;
  status: string;
  user_status?: string;
}

export interface DirectoryDetail extends DirectoryRow {
  contact_name?: string;
  owner_user_id?: string;
  owner_user_status?: string;
  user_id?: string;
  user_status?: string;
  members?: DirectoryMember[];
  in_flight_jobs: { id: string; reference: string; status: string }[];
  interventions: Intervention[];
  user_interventions: Intervention[];
}

export interface RevealedContact {
  name: string;
  phone: string;
}

export interface InterventionRequest {
  account_type: AccountType;
  account_id: string;
  action: InterventionAction;
  reason: string;
  duration_days?: number | null;
}

export interface ConfigVersion {
  version: number;
  changed_by_user_id: string | null;
  changed_by_name: string | null;
  rationale: string;
  created_at: string;
}

export interface ConfigView {
  version: number;
  config: Record<string, unknown>;
  editable_paths: string[];
  versions: ConfigVersion[];
}

export interface ConfigChange {
  path: string;
  before: unknown;
  after: unknown;
}

export interface ConfigPreview {
  version: number;
  changes: ConfigChange[];
  /** Fikisha's fee on sample prices, both sides together and per side
   * (ADR-2D-55). */
  commission_samples: {
    agreed_price_kes: number;
    before_kes: number;
    after_kes: number;
    before?: { business_kes: number; operator_kes: number };
    after?: { business_kes: number; operator_kes: number };
  }[];
}

export interface LedgerAdjustment {
  id: string;
  kind: string;
  amount_kes: number;
  reason: string;
  by_platform_admin: boolean;
  source_dispute_id: string | null;
  created_at: string;
}

export interface LedgerRow {
  id: string;
  job_id: string;
  job_reference: string;
  business_name: string | null;
  /** Which side owes this record (ADR-2D-55). */
  party: 'BUSINESS' | 'OPERATOR';
  /** Who owes it: the business for the business side, else the operator
   * or group. */
  payee: { kind: 'OPERATOR' | 'GROUP' | 'BUSINESS'; id: string; name: string | null };
  agreed_price_kes: number;
  rate: string;
  /** Only records from before the split had a minimum and a cap. */
  min_fee_kes: number | null;
  cap_kes: number | null;
  commission_kes: number;
  adjustments_kes: number;
  effective_kes: number;
  config_version: number | null;
  adjustments: LedgerAdjustment[];
  created_at: string;
}

export interface LedgerTotals {
  records: number;
  commission_kes: number;
  adjustments_kes: number;
  effective_kes: number;
}

export type LedgerPage = Paged<LedgerRow> & { totals: LedgerTotals; statements_available: boolean };
