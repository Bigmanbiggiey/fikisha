import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Route, Routes } from 'react-router-dom';

import { HomePage } from '@/features/home/HomePage';
import { MorePage } from '@/features/more/MorePage';
import { renderWithProviders } from '@/test/renderWithProviders';

import { isNavItemActive, NAV, type NavRole } from './navConfig';
import { RoleSidebar } from './RoleSidebar';
import { RoleTabBar } from './RoleTabBar';

const setRole = vi.fn();
let active: { role: NavRole | null; roles: NavRole[] } = { role: 'BUSINESS', roles: ['BUSINESS'] };

vi.mock('@/shell/activeRole', () => ({
  useActiveRole: () => ({ loading: false, setRole, ...active }),
}));
vi.mock('@/shell/useWorkspaces', () => ({
  useWorkspaces: () => ({
    loading: false,
    workspaces: [
      { kind: 'BUSINESS', id: 'b1', label: 'Mama Njeri Hardware' },
      { kind: 'OPERATOR', id: 'op1', label: 'A. Otieno' },
    ],
  }),
}));
vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: () => Promise.reject(new Error('anon')), logout: vi.fn() },
}));

function tabNames(): string[] {
  const bar = screen.getByRole('navigation', { name: 'Main' });
  return within(bar)
    .getAllByRole('link')
    .map((a) => a.textContent ?? '');
}

describe('role navigation (Design Phase 7 P-04)', () => {
  beforeEach(() => {
    setRole.mockReset();
    active = { role: 'BUSINESS', roles: ['BUSINESS'] };
  });

  it.each<[NavRole, string[]]>([
    ['BUSINESS', ['Home', 'Jobs', 'Request transport', 'More']],
    ['OPERATOR', ['Home', 'Work', 'My Jobs', 'More']],
    ['DRIVER', ['Current job', 'Jobs', 'More']],
    ['GROUP_MANAGER', ['Home', 'Jobs', 'More']],
    ['OPERATIONS_OFFICER', ['Operations', 'Monitor', 'Verification', 'More']],
    ['PLATFORM_ADMIN', ['Operations', 'Monitor', 'Verification', 'More']],
  ])('the %s tab bar lists exactly its items', (role, expected) => {
    active = { role, roles: [role] };
    renderWithProviders(<RoleTabBar />);
    expect(tabNames()).toEqual(expected);
  });

  it('never shows a business Diagnostics, Operator or Groups', () => {
    renderWithProviders(
      <>
        <RoleTabBar />
        <RoleSidebar />
        <MorePage />
      </>,
    );
    for (const name of [/Diagnostics/, /^Operator$/, /Groups/]) {
      expect(screen.queryByRole('link', { name })).not.toBeInTheDocument();
    }
    // Business's own secondary item is there.
    expect(screen.getAllByRole('link', { name: /Businesses/ }).length).toBeGreaterThan(0);
  });

  it('hides the tab bar from md up and shows the sidebar only from lg', () => {
    const { container } = renderWithProviders(
      <>
        <RoleTabBar />
        <RoleSidebar />
      </>,
    );
    expect(container.querySelector('nav.fixed')).toHaveClass('md:hidden');
    expect(container.querySelector('aside')).toHaveClass('hidden', 'lg:block');
  });

  it('gives tab items the 56 px driver target and marks the current page', () => {
    renderWithProviders(<RoleTabBar />, { route: '/jobs/abc' });
    const jobs = screen.getByRole('link', { name: 'Jobs' });
    expect(jobs).toHaveClass('min-h-target-driver');
    expect(jobs).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('link', { name: 'Home' })).not.toHaveAttribute('aria-current');
  });

  it('puts the language switcher and sign out in More', () => {
    renderWithProviders(<MorePage />);
    expect(screen.getByRole('combobox', { name: 'Language' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Sign out' })).toBeInTheDocument();
  });

  it('offers the role switch only to people with more than one role', async () => {
    const { unmount } = renderWithProviders(<MorePage />);
    expect(screen.queryByRole('radio')).not.toBeInTheDocument();
    unmount();

    active = { role: 'BUSINESS', roles: ['BUSINESS', 'OPERATOR'] };
    const user = userEvent.setup();
    renderWithProviders(
      <Routes>
        <Route path="/more" element={<MorePage />} />
        <Route path="/home" element={<div>Home screen</div>} />
      </Routes>,
      { route: '/more' },
    );
    expect(screen.getByRole('radio', { name: /Business/ })).toBeChecked();
    expect(screen.getByRole('radio', { name: /Business/ })).toHaveAccessibleDescription('Mama Njeri Hardware');

    await user.click(screen.getByRole('radio', { name: /Operator/ }));
    expect(setRole).toHaveBeenCalledWith('OPERATOR');
    expect(await screen.findByText('Home screen')).toBeInTheDocument();
  });

  it("sends a driver's Home to Current job", async () => {
    active = { role: 'DRIVER', roles: ['DRIVER'] };
    renderWithProviders(
      <Routes>
        <Route path="/home" element={<HomePage />} />
        <Route path="/current-job" element={<div>Current job screen</div>} />
      </Routes>,
      { route: '/home' },
    );
    expect(await screen.findByText('Current job screen')).toBeInTheDocument();
  });

  it('matches items to the right paths', () => {
    const [home, jobs] = NAV.BUSINESS.primary;
    expect(isNavItemActive(NAV.BUSINESS.action!, '/jobs/new')).toBe(true);
    expect(isNavItemActive(jobs!, '/jobs/new')).toBe(false);
    expect(isNavItemActive(jobs!, '/jobs/123')).toBe(true);
    expect(isNavItemActive(home!, '/home/x')).toBe(false);
    // A driver's job pages belong to "Current job".
    expect(isNavItemActive(NAV.DRIVER.primary[0]!, '/jobs/123')).toBe(true);
    expect(isNavItemActive(NAV.DRIVER.primary[1]!, '/jobs/123')).toBe(false);
    // "/ops" is exact; the monitor is its own item.
    expect(isNavItemActive(NAV.OPERATIONS_OFFICER.primary[0]!, '/ops/jobs')).toBe(false);
  });
});
