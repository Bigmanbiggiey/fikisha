import type { BadgeTone } from '@/components/StatusBadge';
import { formatDate } from '@/services/datetime';

import type { StatementSummary } from './types';

/** "5 Oct 2026 – 11 Oct 2026": a statement's Mon–Sun week, Kenya dates. */
export function periodLabel(
  s: Pick<StatementSummary, 'period_start' | 'period_end'>,
  language?: string,
): string {
  return `${formatDate(s.period_start, language)} – ${formatDate(s.period_end, language)}`;
}

/** The badge for a statement: overdue outranks unpaid/part-paid (D-8). */
export function stateBadge(s: Pick<StatementSummary, 'state' | 'overdue'>): {
  key: string;
  tone: BadgeTone;
} {
  if (s.state === 'PAID') return { key: 'PAID', tone: 'success' };
  if (s.overdue) return { key: 'OVERDUE', tone: 'danger' };
  return s.state === 'PART_PAID'
    ? { key: 'PART_PAID', tone: 'warning' }
    : { key: 'UNPAID', tone: 'neutral' };
}
