/** Commission statements (Commission & Statements S-2, ADR-2D-42). Every
 * `*_kes` is integer KES minor units. Since the commission split
 * (ADR-2D-55) a business gets statements for its own 5% too. */

export type PayeeKind = 'OPERATOR' | 'GROUP' | 'BUSINESS';
/** Who owes a commission record: the business's side or the operator's. */
export type CommissionParty = 'BUSINESS' | 'OPERATOR';

export type StatementState = 'UNPAID' | 'PART_PAID' | 'PAID';

export interface StatementSummary {
  id: string;
  /** `ST-` + 6 characters; also the paybill account number (D-3). */
  reference: string;
  payee: { kind: PayeeKind; id: string; name: string | null };
  /** Kenya dates, Monday to Sunday. */
  period_start: string;
  period_end: string;
  gross_commission_kes: number;
  /** Zero or negative. */
  adjustments_kes: number;
  /** Can be negative when a credit outweighs the week's commission. */
  net_due_kes: number;
  settled_kes: number;
  outstanding_kes: number;
  state: StatementState;
  overdue: boolean;
  generated_at: string;
  /** List rows only: whether the caller has opened it (D-6). */
  seen?: boolean;
}

export interface StatementLine {
  id: string;
  kind: 'COMMISSION' | 'ADJUSTMENT';
  job_id: string;
  job_reference: string;
  agreed_price_kes: number | null;
  amount_kes: number;
}

export interface StatementSettlement {
  id: string;
  kind: 'PAYMENT' | 'REVERSAL';
  amount_kes: number;
  method: 'MPESA_PAYBILL' | 'BANK' | 'OTHER';
  payment_ref: string;
  paid_on: string;
  note: string;
  reverses: string | null;
  reversed: boolean;
  recorded_at: string;
}

export interface StatementDetail extends StatementSummary {
  lines: StatementLine[];
  settlements: StatementSettlement[];
  /** `paybill_number` is null until Fikisha sets it ("details to follow"). */
  payment: { paybill_number: string | null; account_reference: string };
}

export interface StatementsPage {
  data: StatementSummary[];
  page: { next_cursor: string | null; prev_cursor: string | null };
  unseen_count: number;
}

/** One side's commission on one job: "Earnings for this job" for the
 * operator side, "Cost for this job" for the business side. */
export interface JobEarnings {
  job_id: string;
  party: CommissionParty;
  payee_kind: PayeeKind;
  payee_id: string;
  agreed_price_kes: number;
  /** e.g. "0.0500" */
  rate: string;
  commission_kes: number;
  adjustments_kes: number;
  effective_commission_kes: number;
  /** Operator side only. */
  net_to_operator_kes?: number;
  /** Business side only: the agreed price plus Fikisha's fee. */
  total_cost_kes?: number;
  /** Null when not billed yet, or when the caller may not open it (a
   * business Dispatcher: statements are the Owner's). */
  statement: { id: string; reference: string } | null;
  /** The sides this caller may see on this job. */
  sides: CommissionParty[];
}

/** Staff list (`GET /admin/statements`, S-3). Totals cover the whole filter. */
export interface AdminStatementsPage {
  data: StatementSummary[];
  page: { next_cursor: string | null; prev_cursor: string | null };
  totals: {
    statements: number;
    invoiced_kes: number;
    settled_kes: number;
    outstanding_kes: number;
  };
}

export interface RunResult {
  period_start: string;
  period_end: string;
  statements_created: number;
  statement_ids: string[];
  payees_skipped_existing: number;
}

export interface PaymentInput {
  amount_kes: number;
  payment_ref: string;
  /** YYYY-MM-DD */
  paid_on: string;
  method: StatementSettlement['method'];
  note: string;
}
