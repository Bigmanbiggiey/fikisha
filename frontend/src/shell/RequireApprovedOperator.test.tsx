import { screen } from '@testing-library/react';
import { Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/renderWithProviders';

import type { NavRole } from './navConfig';
import { RequireApprovedOperator } from './RequireApprovedOperator';

let active: { role: NavRole | null; operatorPending: boolean } = { role: 'OPERATOR', operatorPending: true };

vi.mock('@/shell/activeRole', () => ({
  useActiveRole: () => ({ loading: false, roles: [], setRole: vi.fn(), ...active }),
}));
vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: () => Promise.reject(new Error('anon')), logout: vi.fn() },
}));

function renderAt(): void {
  renderWithProviders(
    <Routes>
      <Route path="/home" element={<p>Home page</p>} />
      <Route
        path="/work"
        element={
          <RequireApprovedOperator>
            <p>Work page</p>
          </RequireApprovedOperator>
        }
      />
    </Routes>,
    { route: '/work' },
  );
}

describe('RequireApprovedOperator (assessment 2026-10-19 D-2)', () => {
  beforeEach(() => {
    active = { role: 'OPERATOR', operatorPending: true };
  });

  it('sends an operator awaiting approval home', () => {
    renderAt();
    expect(screen.getByText('Home page')).toBeInTheDocument();
    expect(screen.queryByText('Work page')).not.toBeInTheDocument();
  });

  it('lets an approved operator through', () => {
    active = { role: 'OPERATOR', operatorPending: false };
    renderAt();
    expect(screen.getByText('Work page')).toBeInTheDocument();
  });

  it('lets the same person through while they work as a business', () => {
    active = { role: 'BUSINESS', operatorPending: true };
    renderAt();
    expect(screen.getByText('Work page')).toBeInTheDocument();
  });
});
