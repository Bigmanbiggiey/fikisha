/**
 * "5 min ago" / "dakika 5 zilizopita" for the inbox rows. A small local
 * helper; Design Phase 7 P-14 (sub-increment 10d) builds the shared date and
 * time helper, which should replace this.
 */
export function relativeAge(iso: string, language: string, now: number = Date.now()): string {
  const locale = language.startsWith('sw') ? 'sw' : 'en';
  const seconds = (new Date(iso).getTime() - now) / 1000;
  const abs = Math.abs(seconds);
  const rtf = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' });
  if (abs < 60) return rtf.format(0, 'minute');
  if (abs < 3600) return rtf.format(Math.round(seconds / 60), 'minute');
  if (abs < 86_400) return rtf.format(Math.round(seconds / 3600), 'hour');
  if (abs < 7 * 86_400) return rtf.format(Math.round(seconds / 86_400), 'day');
  return new Date(iso).toLocaleDateString(locale, { day: 'numeric', month: 'short' });
}
