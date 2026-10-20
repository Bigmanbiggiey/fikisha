import { describe, expect, it } from 'vitest';

import { NAV } from './navConfig';

describe('admin menu icons (assessment 2026-10-20 L-6)', () => {
  it('uses the founder’s icons for the staff screens', () => {
    const icons = Object.fromEntries(
      [...NAV.PLATFORM_ADMIN.primary, ...NAV.PLATFORM_ADMIN.secondary].map((i) => [i.to, i.icon]),
    );
    expect(icons['/ops/jobs']).toBe('eye');
    expect(icons['/verification']).toBe('check');
    expect(icons['/admin/commission']).toBe('coins');
    expect(icons['/ops']).toBe('settings');
    expect(icons['/ops/audit']).toBe('search');
  });
});
