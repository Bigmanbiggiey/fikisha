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
