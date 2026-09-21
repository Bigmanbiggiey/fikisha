import type { JobStatus } from './types';

/** The Jobs list is segmented (`design-phase-3-wireframes.md` §6.5) — never
 * the raw 14 states as tabs. `DRAFT` isn't named in that section explicitly;
 * grouped under "requests" here as "not yet moving", the closest fit. */
export type JobSegment = 'active' | 'requests' | 'completed' | 'cancelled';

const SEGMENT_BY_STATUS: Record<JobStatus, JobSegment> = {
  DRAFT: 'requests',
  REQUESTED: 'requests',
  NEGOTIATING: 'requests',
  CONFIRMED: 'active',
  ASSIGNED: 'active',
  AT_PICKUP: 'active',
  PICKED_UP: 'active',
  IN_TRANSIT: 'active',
  AT_DESTINATION: 'active',
  DELIVERED: 'active',
  DISPUTED: 'active',
  COMPLETED: 'completed',
  CANCELLED: 'cancelled',
  FAILED: 'cancelled',
};

export function segmentFor(status: JobStatus): JobSegment {
  return SEGMENT_BY_STATUS[status];
}

export type BusinessActionKey =
  | 'continueRequest'
  | 'reviewOffers'
  | 'confirmPickup'
  | 'confirmCompletion'
  | 'viewSummary'
  | 'viewDispute';

/** The Business's one primary next action per state (`design-phase-3-
 * wireframes.md` §6.4's table) — states not listed here have nothing for the
 * business to do (monitoring only; secondary actions like Cancel/Report an
 * issue live under `·`, not as the primary `⌘`).
 *
 * Known simplifications/gaps, all documented rather than silently
 * approximated or faked:
 * - **`confirmPickup`**: the wireframe shows this only when the driver has
 *   *requested* business-side confirmation (or OTP is unavailable) — that
 *   needs an in-app notification signal Phase 2D's backend doesn't expose
 *   (no such field on the Job view, no notifications API in
 *   `phase-2d-api.md`). `confirm-pickup/business` is unconditionally one of
 *   the two always-valid pickup proofs at `AT_PICKUP`, so this surfaces it
 *   whenever the job is `AT_PICKUP` — functionally correct, more proactive
 *   than the ideal request-gated UX.
 * - **`confirmCompletion`**: the wireframe names this as a Business action
 *   at `DELIVERED`, but there is no such endpoint — `DELIVERED -> COMPLETED`
 *   only ever happens automatically (`jobs.tasks.autocomplete_delivered`,
 *   ADR-2D-29). The UI renders this as informational, not a real button.
 * - **`viewDispute`** (→ dispute detail) points at a screen that doesn't
 *   exist yet (Increment 7) — rendered as an informational state with a
 *   "coming in a later update" note, not a dead link. `reviewOffers` (→
 *   Negotiation) was the same until Increment 3, which built it. */
/** The subset of `businessNextAction` states worth surfacing under "Needs
 * your action" on Business Home (§6.1's example: a counter-offer and a
 * pending delivery confirmation) — narrower than every state that merely
 * *has* a next action: a `DRAFT` is an unfinished job, not an urgent one,
 * and `CANCELLED`/`FAILED`'s "View summary" is informational, not a call to
 * action, so both are excluded here even though `businessNextAction`
 * returns non-null for them. */
export function needsBusinessAttention(status: JobStatus): boolean {
  return status === 'NEGOTIATING' || status === 'AT_PICKUP' || status === 'DELIVERED' || status === 'DISPUTED';
}

/** The happy-path order the timeline renders (`design-phase-3-wireframes.md`
 * §6.4/§14) — `NEGOTIATING` is folded into the same slot as `REQUESTED`
 * (negotiation doesn't get its own timeline row; it's shown via Messages).
 * `DRAFT` never appears here (a DRAFT job isn't visible/active yet). */
export const HAPPY_PATH_STATUSES: readonly JobStatus[] = [
  'REQUESTED',
  'CONFIRMED',
  'ASSIGNED',
  'AT_PICKUP',
  'PICKED_UP',
  'IN_TRANSIT',
  'AT_DESTINATION',
  'DELIVERED',
  'COMPLETED',
];

export function happyPathIndex(status: JobStatus): number {
  if (status === 'NEGOTIATING') return HAPPY_PATH_STATUSES.indexOf('REQUESTED');
  return HAPPY_PATH_STATUSES.indexOf(status);
}

/** The short human-friendly reference shown for a Job across every screen
 * (last 6 chars of the UUIDv7 id, uppercased) — a single source so the
 * derivation rule only has to change in one place. */
export function jobReference(id: string): string {
  return id.slice(-6).toUpperCase();
}

/** My Jobs segmentation for the Operator (`design-phase-3-wireframes.md`
 * §7.5: Active/Upcoming/Completed/Cancelled-disputed) — a different mapping
 * from the Business's `segmentFor`, since the same job status means a
 * different thing to look at from the operator's side (e.g. `CONFIRMED`
 * reads as "upcoming work" to an operator, not "active"). */
export type OperatorSegment = 'active' | 'upcoming' | 'completed' | 'cancelled';

const OPERATOR_SEGMENT_BY_STATUS: Record<JobStatus, OperatorSegment> = {
  DRAFT: 'upcoming',
  REQUESTED: 'upcoming',
  NEGOTIATING: 'upcoming',
  CONFIRMED: 'upcoming',
  ASSIGNED: 'active',
  AT_PICKUP: 'active',
  PICKED_UP: 'active',
  IN_TRANSIT: 'active',
  AT_DESTINATION: 'active',
  DELIVERED: 'active',
  DISPUTED: 'active',
  COMPLETED: 'completed',
  CANCELLED: 'cancelled',
  FAILED: 'cancelled',
};

export function operatorSegmentFor(status: JobStatus): OperatorSegment {
  return OPERATOR_SEGMENT_BY_STATUS[status];
}

export type OperatorActionKey =
  | 'respond'
  | 'assignDriverVehicle'
  | 'startPickup'
  | 'viewStatement'
  | 'viewSummary'
  | 'viewDispute';

/** The Operator's one primary next action per state
 * (`design-phase-3-wireframes.md` §7.4's table) — `isAssignedDriver` is
 * whether *this* viewing operator is the job's `assigned_driver_id` (an
 * individual operator always is, once assigned; a Group Manager who is not
 * personally driving is not).
 *
 * Known simplifications, documented rather than silently approximated:
 * - **`startPickup`**: the actual pickup/custody flow (OTP confirm, arrive/
 *   transit/deliver) is Increment 5 (Driver) scope — not built yet. Rendered
 *   as an informational "coming in a later update" state, the same pattern
 *   `viewDispute` used before its own increment existed.
 *   `ASSIGNED`-but-not-the-driver is read-only (`null` — nothing to do),
 *   matching the wireframe exactly.
 * - **`viewStatement`** ("Earnings for this Job"): deferred this increment
 *   — `commission.read` is Platform-Admin-only (ADR-2D-27) and there is no
 *   operator-facing commission-preview endpoint yet. Informational only. */
export function operatorNextAction(
  status: JobStatus,
  isAssignedDriver: boolean,
): OperatorActionKey | null {
  switch (status) {
    case 'NEGOTIATING':
      return 'respond';
    case 'CONFIRMED':
      return 'assignDriverVehicle';
    case 'ASSIGNED':
      return isAssignedDriver ? 'startPickup' : null;
    case 'COMPLETED':
      return 'viewStatement';
    case 'CANCELLED':
    case 'FAILED':
      return 'viewSummary';
    case 'DISPUTED':
      return 'viewDispute';
    default:
      return null;
  }
}

/** Mirrors `needsBusinessAttention` for the Operator's Home "needs response"
 * bucket (`design-phase-3-wireframes.md` §7.1) — a `NEGOTIATING` thread
 * awaiting the operator's reply, or a `CONFIRMED` job still needing a
 * driver/vehicle assigned. */
export function needsOperatorAttention(status: JobStatus): boolean {
  return status === 'NEGOTIATING' || status === 'CONFIRMED' || status === 'DISPUTED';
}

export function businessNextAction(status: JobStatus): BusinessActionKey | null {
  switch (status) {
    case 'DRAFT':
      return 'continueRequest';
    case 'NEGOTIATING':
      return 'reviewOffers';
    case 'AT_PICKUP':
      return 'confirmPickup';
    case 'DELIVERED':
      return 'confirmCompletion';
    case 'CANCELLED':
    case 'FAILED':
      return 'viewSummary';
    case 'DISPUTED':
      return 'viewDispute';
    default:
      return null;
  }
}
