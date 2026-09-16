/** Field names/shapes taken directly from `fikisha.negotiation.services._thread_payload()`
 * / `selectors.annotate_entries()` — see `docs/phase-2/phase-2d-api.md` §3. */

export const THREAD_STATUSES = ['ACTIVE', 'SUPERSEDED', 'CLOSED'] as const;
export type ThreadStatus = (typeof THREAD_STATUSES)[number];

export const ENTRY_TYPES = ['PROPOSE', 'COUNTER', 'ACCEPT', 'REJECT'] as const;
export type EntryType = (typeof ENTRY_TYPES)[number];

/** Derived at read time — never stored (ADR-2D-11). */
export const ENTRY_STATUSES = ['ACTIVE', 'SUPERSEDED', 'EXPIRED'] as const;
export type EntryStatus = (typeof ENTRY_STATUSES)[number];

export const ENTRY_ACTOR_ROLES = ['BUSINESS', 'OPERATOR', 'ADMIN'] as const;
export type EntryActorRole = (typeof ENTRY_ACTOR_ROLES)[number];

export interface NegotiationEntry {
  id: string;
  actor_role: EntryActorRole;
  type: EntryType;
  amount_kes: number | null;
  note: string;
  in_response_to_id: string | null;
  created_at: string;
  expires_at: string | null;
  effective_status: EntryStatus;
}

export interface StandingOffer {
  entry_id: string;
  actor_role: EntryActorRole;
  amount_kes: number;
}

/** The *viewer's* own counterparty offer — what they specifically could
 * accept right now, as opposed to `standing_offer` (whoever posted last,
 * either side). `null` when there's nothing of the counterparty's to
 * accept (e.g. the viewer's own offer is the most recent one on the
 * table). Server-computed (`counterparty_figure_to_accept()`), not
 * re-derived here. */
export interface CounterpartyOffer {
  entry_id: string;
  amount_kes: number;
}

export interface MutualAcceptance {
  reached: boolean;
  amount_kes: number | null;
  entry_ids: string[];
}

export interface NegotiationThread {
  thread_id: string;
  job_id: string;
  job_status: string;
  status: ThreadStatus;
  operator_party: 'OPERATOR' | 'GROUP';
  operator_id: string | null;
  group_id: string | null;
  /** The operator's (or group's) public name — resolved server-side so the
   * frontend never needs `operator.read`/`group.read` access to an
   * arbitrary id (those stay closed to everyone but the profile's own
   * owner). `null` is a genuine gap (e.g. a since-deleted profile), not
   * "loading". */
  operator_display_name: string | null;
  standing_offer: StandingOffer | null;
  counterparty_offer: CounterpartyOffer | null;
  mutual_acceptance: MutualAcceptance;
  entries: NegotiationEntry[];
  /** Only present on a `propose()` response when the figure is a notable
   * outlier vs. the baseline — a warning, not a validation error. */
  warning?: string;
}

/** `job_id` is a URL param (`POST /jobs/:jobId/negotiation/threads`), not
 * part of the body. Exactly one of `operator_id`/`group_id` is required. */
export interface ProposeBody {
  operator_id?: string;
  group_id?: string;
  amount_kes: number;
  note?: string;
}

export interface CounterBody {
  amount_kes: number;
  note?: string;
}

/** `amount_kes` is optional — omit to accept whatever the counterparty's
 * current standing figure is; include it as a defence-in-depth confirmation
 * of the exact amount being accepted. */
export interface AcceptBody {
  amount_kes?: number;
}

export interface DeclineBody {
  note?: string;
}

/** `accept()`'s response is the thread payload plus whether *this* accept
 * reached mutual acceptance — both sides must independently accept for the
 * same amount (`mutual_acceptance.reached`); a single accept only writes
 * this side's entry and leaves the thread `ACTIVE`. */
export interface AcceptResult extends NegotiationThread {
  confirmed: boolean;
}
