import { describe, expect, it } from 'vitest';

import { breakpoint } from './tokens';

/**
 * Guard for Design Phase 7 F-01. This project's `sm` breakpoint is the
 * **baseline phone (360px)**, not Tailwind's default 640px, so `sm:`
 * multi-column or row layouts split the smallest phone into squeezed
 * columns. Multi-column layouts start at `md:` (600px) or `lg:` (900px).
 */
const SOURCES = import.meta.glob('/src/**/*.tsx', { query: '?raw', import: 'default', eager: true }) as Record<
  string,
  string
>;
const FORBIDDEN = /\bsm:(grid-cols-|col-span-|flex-row)/;

describe('breakpoint guard', () => {
  it('confirms sm is the 360px baseline phone', () => {
    expect(breakpoint.sm).toBe('360px');
  });

  it('has no sm: multi-column or row layouts anywhere in src', () => {
    const offenders = Object.entries(SOURCES)
      .filter(([path]) => !path.endsWith('.test.tsx'))
      .flatMap(([path, text]) =>
        text
          .split('\n')
          .map((line, i) => ({ path, line: i + 1, text: line.trim() }))
          .filter((l) => FORBIDDEN.test(l.text)),
      );
    expect(offenders).toEqual([]);
  });
});
