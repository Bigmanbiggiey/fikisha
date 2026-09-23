import { describe, expect, it } from 'vitest';

import { resources } from './index';

/** Every English key must exist in Swahili and vice versa — both are
 * first-class languages (CLAUDE.md §2), so a missing key is a real defect,
 * not a fallback. */
function keysOf(obj: unknown, prefix = ''): string[] {
  if (obj === null || typeof obj !== 'object') return [prefix];
  return Object.entries(obj as Record<string, unknown>).flatMap(([k, v]) =>
    keysOf(v, prefix ? `${prefix}.${k}` : k),
  );
}

describe('en/sw locale parity', () => {
  for (const ns of Object.keys(resources.en) as (keyof typeof resources.en)[]) {
    it(`namespace "${ns}" has the same keys in en and sw`, () => {
      const en = keysOf(resources.en[ns]).sort();
      const sw = keysOf(resources.sw[ns]).sort();
      expect(sw.filter((k) => !en.includes(k))).toEqual([]);
      expect(en.filter((k) => !sw.includes(k))).toEqual([]);
    });
  }
});
