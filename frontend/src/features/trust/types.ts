/** Operator tiers (operator-tiers plan, ADR-2D-52). */
export type TierLevel = 'L0' | 'L1' | 'L2' | 'L3' | 'RESTRICTED';
export type StoredTier = Exclude<TierLevel, 'L0'>;
export const STORED_TIERS: StoredTier[] = ['L1', 'L2', 'L3', 'RESTRICTED'];

export interface TierCriterion {
  key: string;
  status: 'MET' | 'NOT_MET' | 'NOT_MEASURED';
  current: number | null;
  target: number | null;
}

export interface TierChange {
  id: string;
  from_level: TierLevel;
  to_level: TierLevel;
  trigger: 'AUTO_PROPOSED' | 'ADMIN_CONFIRMED' | 'ADMIN_REJECTED' | 'ADMIN_OVERRIDE';
  status: 'PROPOSED' | 'APPLIED' | 'REJECTED';
  reason: string;
  created_at: string;
  /** Staff only: who made the change. */
  by?: string;
}

export interface TierView {
  operator_id: string;
  operator_name: string;
  level: TierLevel;
  stored_level: StoredTier;
  floor_met: boolean;
  since: string | null;
  bands: string[];
  /** KES minor units; null = no cap (VERY_HIGH still needs per-job approval). */
  max_value_kes: number | null;
  next_level: TierLevel | null;
  criteria: TierCriterion[];
  ready_for_review: boolean;
  open_proposal: TierChange | null;
  history: TierChange[];
}

export interface TierProposal extends TierChange {
  operator_id: string;
  operator_name: string;
}
