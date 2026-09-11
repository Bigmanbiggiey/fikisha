import { screen, waitFor } from '@testing-library/react';
import { Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/renderWithProviders';

import { HomeOrLanding } from './HomeOrLanding';

const me = vi.fn();

vi.mock('@/features/auth/authApi', () => ({
  authApi: {
    me: (...args: unknown[]) => me(...args),
    logout: vi.fn(),
  },
}));

function renderAtRoot(): void {
  renderWithProviders(
    <Routes>
      <Route path="/" element={<HomeOrLanding />} />
      <Route path="/home" element={<div>dashboard-stub</div>} />
    </Routes>,
    { route: '/' },
  );
}

describe('HomeOrLanding', () => {
  beforeEach(() => {
    me.mockReset();
  });

  it('shows the public landing page to a signed-out visitor, with no redirect to /login', async () => {
    me.mockRejectedValue(new Error('anonymous'));
    renderAtRoot();

    await screen.findByRole('button', { name: /^sign in$/i });
    expect(screen.queryByText('dashboard-stub')).not.toBeInTheDocument();
  });

  it('sends an already-signed-in visitor straight to /home', async () => {
    me.mockResolvedValue({
      id: 'u1',
      phone: '+254700000001',
      display_name: '',
      locale: 'en',
      status: 'ACTIVE',
      roles: [],
      is_admin: false,
    });
    renderAtRoot();

    await waitFor(() => expect(screen.getByText('dashboard-stub')).toBeInTheDocument());
  });
});
