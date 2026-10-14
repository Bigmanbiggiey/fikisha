import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { formatDate, formatDateTime, formatRelative, formatStamp, formatTime, isToday } from './datetime';

// 06:30 UTC is 09:30 in Nairobi (EAT, UTC+3, no daylight saving).
const ISO = '2026-10-14T06:30:00Z';

describe('datetime (P-14)', () => {
  const originalTz = process.env.TZ;
  beforeEach(() => {
    // A device far from Kenya: output must not depend on it.
    process.env.TZ = 'America/Los_Angeles';
  });
  afterEach(() => {
    process.env.TZ = originalTz;
  });

  it('shows Kenya time whatever the device time zone', () => {
    expect(formatTime(ISO, 'en')).toBe('09:30');
    expect(formatDateTime(ISO, 'en')).toBe('14 Oct 2026, 09:30');
    expect(formatDate('2026-10-13T22:30:00Z', 'en')).toBe('14 Oct 2026');
  });

  it('writes Swahili for the sw language', () => {
    expect(formatDate(ISO, 'sw')).toContain('Okt');
    expect(formatRelative('2026-10-14T06:25:00Z', 'sw', Date.parse(ISO))).toBe('dakika 5 zilizopita');
    expect(formatRelative('2026-10-13T06:30:00Z', 'sw', Date.parse(ISO))).toBe('jana');
  });

  it('treats "today" as the Kenyan calendar day', () => {
    const now = Date.parse('2026-10-14T20:00:00Z'); // 23:00 in Nairobi
    expect(isToday('2026-10-13T21:30:00Z', now)).toBe(true); // 00:30 on the 14th in Nairobi
    expect(isToday('2026-10-13T20:30:00Z', now)).toBe(false); // 23:30 on the 13th
  });

  it('gives timeline rows a date once they are older than today', () => {
    const now = Date.parse(ISO);
    expect(formatStamp('2026-10-14T05:00:00Z', 'en', now)).toBe('08:00');
    expect(formatStamp('2026-10-12T05:00:00Z', 'en', now)).toBe('12 Oct 2026, 08:00');
  });

  it('shows a plain date for anything older than a week', () => {
    expect(formatRelative('2026-09-01T06:30:00Z', 'en', Date.parse(ISO))).toBe('1 Sept');
  });

  it('never throws on a bad value', () => {
    expect(formatDateTime('not a date', 'en')).toBe('—');
    expect(formatRelative('not a date', 'en')).toBe('—');
  });
});
