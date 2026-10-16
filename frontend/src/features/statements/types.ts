/** Commission statements (Commission & Statements S-2, ADR-2D-42). Every
 * `*_kes` is integer KES minor units. */

export type StatementState = 'UNPAID' | 'PART_PAID' | 'PAID';

export interface StatementSummary {
  id: string;
  /** `ST-` + 6 characters; also the paybill account number (D-3). */
  reference: string;
  payee: { kind: 'OPERATOR' | 'GROUP'; id: string; name: string | null };
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

export interface JobEarnings {
  job_id: string;
  payee_kind: 'OPERATOR' | 'GROUP';
  payee_id: string;
  agreed_price_kes: number;
  commission_kes: number;
  adjustments_kes: number;
  effective_commission_kes: number;
  net_to_operator_kes: number;
  statement: { id: string; reference: string } | null;
}
