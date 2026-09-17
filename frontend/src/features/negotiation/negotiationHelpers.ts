import type { BadgeTone } from '@/components/StatusBadge';
import type { IconName } from '@/design/Icon';

import type { EntryStatus, EntryType, NegotiationEntry } from './types';

/** `design-phase-3-wireframes.md` §8.1's per-card status word — computed
 * from the entry's already-server-derived `effective_status` plus its
 * `type` (an EXPIRED/SUPERSEDED ACCEPT reads as "Declined"/"Countered" too,
 * but the wireframe only names the offer-card states explicitly; accept/
 * reject entries get their own fixed words below since they're terminal by
 * construction). */
export function entryStatusLabel(entry: Pick<NegotiationEntry, 'type' | 'effective_status'>): string {
  if (entry.type === 'REJECT') return 'declined';
  if (entry.type === 'ACCEPT') {
    switch (entry.effective_status) {
      case 'EXPIRED':
        return 'declined';
      case 'SUPERSEDED':
        return 'countered';
      default:
        return 'accepted';
    }
  }
  switch (entry.effective_status) {
    case 'ACTIVE':
      return 'current';
    case 'EXPIRED':
      return 'expired';
    case 'SUPERSEDED':
    default:
      return 'countered';
  }
}

const TONE_BY_LABEL: Record<string, BadgeTone> = {
  current: 'brand',
  accepted: 'success',
  declined: 'danger',
  expired: 'neutral',
  countered: 'neutral',
};

const ICON_BY_LABEL: Record<string, IconName> = {
  current: 'dotCurrent',
  accepted: 'check',
  declined: 'close',
  expired: 'pause',
  countered: 'sync',
};

export function entryStatusTone(label: string): BadgeTone {
  return TONE_BY_LABEL[label] ?? 'neutral';
}

export function entryStatusIcon(label: string): IconName {
  return ICON_BY_LABEL[label] ?? 'dot';
}

/** Who proposed this entry, from the current viewer's point of view — "you",
 * "admin", or a named counterparty (or `null` if the name is unavailable,
 * e.g. a deleted profile — the caller falls back to a translated generic
 * label, never a hardcoded string here). Increment 3 only ever renders
 * with `viewerRole: 'BUSINESS'`; `'OPERATOR'` is wired in Increment 4. */
export function proposerOf(
  entry: Pick<NegotiationEntry, 'actor_role'>,
  viewerRole: 'BUSINESS' | 'OPERATOR',
  operatorDisplayName: string | null,
): { kind: 'you' } | { kind: 'admin' } | { kind: 'counterparty'; name: string | null } {
  if (entry.actor_role === viewerRole) return { kind: 'you' };
  if (entry.actor_role === 'ADMIN') return { kind: 'admin' };
  return { kind: 'counterparty', name: operatorDisplayName };
}

export type { EntryStatus, EntryType };
