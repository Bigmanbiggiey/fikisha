import type { BadgeTone } from '@/components/StatusBadge';
import { formatDate, TIME_ZONE } from '@/services/datetime';

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

/** Today's date in Kenya as YYYY-MM-DD, whatever the device's time zone. */
export function kenyaToday(now: Date = new Date()): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: TIME_ZONE }).format(now);
}

function addDays(iso: string, days: number): string {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

/** The Monday that starts the last finished Mon–Sun week, Kenya time —
 * what the weekly run bills (plan §3.4). */
export function lastWeekStart(now: Date = new Date()): string {
  const today = kenyaToday(now);
  const weekday = (new Date(`${today}T00:00:00Z`).getUTCDay() + 6) % 7; // Monday = 0
  return addDays(today, -weekday - 7);
}

/** The last ``count`` finished weeks' Mondays, newest first. */
export function recentWeekStarts(count: number, now: Date = new Date()): string[] {
  const latest = lastWeekStart(now);
  return Array.from({ length: count }, (_, i) => addDays(latest, -7 * i));
}

/** The Sunday that ends the week starting ``monday``. */
export function weekEnd(monday: string): string {
  return addDays(monday, 6);
}
