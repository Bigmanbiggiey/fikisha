/**
 * Dates and times, one way everywhere (Design Phase 7 P-14, F-14).
 *
 * Always shown in Kenya time (`Africa/Nairobi`, EAT), whatever the device's
 * own time zone, and in the reader's language (`sw-KE` / `en-KE`). The
 * language defaults to the app's active one; components that show dates
 * already re-render on a language switch through `useTranslation`.
 */

import i18n from '@/i18n';

export const TIME_ZONE = 'Africa/Nairobi';

function localeFor(language: string | undefined): string {
  const lang = language ?? i18n.resolvedLanguage ?? 'en';
  return lang.startsWith('sw') ? 'sw-KE' : 'en-KE';
}

function format(iso: string, language: string | undefined, options: Intl.DateTimeFormatOptions): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat(localeFor(language), { timeZone: TIME_ZONE, ...options }).format(date);
}

/** "09:30" */
export function formatTime(iso: string, language?: string): string {
  return format(iso, language, { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' });
}

/** "14 Oct 2026" / "14 Okt 2026" */
export function formatDate(iso: string, language?: string): string {
  return format(iso, language, { day: 'numeric', month: 'short', year: 'numeric' });
}

/** "14 Oct 2026, 09:30" */
export function formatDateTime(iso: string, language?: string): string {
  return format(iso, language, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  });
}

/** The calendar day in Kenya time, as YYYY-MM-DD. */
function kenyaDay(date: Date): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: TIME_ZONE }).format(date);
}

/** Today in Kenya time? */
export function isToday(iso: string, now: number = Date.now()): boolean {
  return kenyaDay(new Date(iso)) === kenyaDay(new Date(now));
}

/** The time for something that happened today, otherwise date and time
 * (timeline rows, P-14). */
export function formatStamp(iso: string, language?: string, now: number = Date.now()): string {
  return isToday(iso, now) ? formatTime(iso, language) : formatDateTime(iso, language);
}

/** "5 min ago" / "dakika 5 zilizopita"; older than a week, the date
 * ("14 Oct" / "14 Okt"). */
export function formatRelative(iso: string, language?: string, now: number = Date.now()): string {
  const seconds = (new Date(iso).getTime() - now) / 1000;
  if (Number.isNaN(seconds)) return '—';
  const abs = Math.abs(seconds);
  const rtf = new Intl.RelativeTimeFormat(localeFor(language), { numeric: 'auto' });
  if (abs < 60) return rtf.format(0, 'minute');
  if (abs < 3600) return rtf.format(Math.round(seconds / 60), 'minute');
  if (abs < 86_400) return rtf.format(Math.round(seconds / 3600), 'hour');
  if (abs < 7 * 86_400) return rtf.format(Math.round(seconds / 86_400), 'day');
  return format(iso, language, { day: 'numeric', month: 'short' });
}
