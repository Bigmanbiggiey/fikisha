import { screen, waitFor } from '@testing-library/react';
import { Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/renderWithProviders';

import { RequireAuth } from './RequireAuth';

const me = vi.fn();

vi.mock('./authApi', () => ({
  authApi: {
    me: (...args: unknown[]) => me(...args),
    logout: vi.fn(),
  },
}));

describe('RequireAuth', () => {
  beforeEach(() => {
    me.mockReset();
  });

  it('only prompts sign-in once a protected route is actually reached, not at /', async () => {
    me.mockRejectedValue(new Error('anonymous'));

    renderWithProviders(
      <Routes>
        <Route path="/" element={<div>public-landing-stub</div>} />
        <Route
          path="/vehicles"
          element={
            <RequireAuth>
              <div>vehicles-stub</div>
            </RequireAuth>
          }
        />
        <Route path="/login" element={<div>login-stub</div>} />
      </Routes>,
      { route: '/vehicles' },
    );

    // Visiting the protected route while signed out lands on /login...
    await waitFor(() => expect(screen.getByText('login-stub')).toBeInTheDocument());
    // ...it never silently falls back to the public landing route instead.
    expect(screen.queryByText('public-landing-stub')).not.toBeInTheDocument();
  });

  it('renders the protected content directly once authenticated', async () => {
    me.mockResolvedValue({
      id: 'u1',
      phone: '+254700000001',
      display_name: '',
      locale: 'en',
      status: 'ACTIVE',
      roles: [],
      is_admin: false,
    });

    renderWithProviders(
      <Routes>
        <Route
          path="/vehicles"
          element={
            <RequireAuth>
              <div>vehicles-stub</div>
            </RequireAuth>
          }
        />
        <Route path="/login" element={<div>login-stub</div>} />
      </Routes>,
      { route: '/vehicles' },
    );

    await waitFor(() => expect(screen.getByText('vehicles-stub')).toBeInTheDocument());
  });
});
