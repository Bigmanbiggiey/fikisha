import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Route, Routes } from 'react-router-dom';

import { renderWithProviders } from '@/test/renderWithProviders';

import { AdminControlPage } from './AdminControlPage';
import { RequirePlatformAdmin } from './RequirePlatformAdmin';

const meMock = vi.fn();
const disputeQueue = vi.fn();
const highValueQueue = vi.fn();

vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: (...a: unknown[]) => meMock(...a), logout: vi.fn() },
}));
vi.mock('@/features/ops/opsApi', () => ({
  opsApi: {
    disputeQueue: (...a: unknown[]) => disputeQueue(...a),
    highValueQueue: (...a: unknown[]) => highValueQueue(...a),
  },
}));

const page = (data: unknown[], next: string | null = null) => ({ data, page: { next_cursor: next, prev_cursor: null } });

function dispute(id: string, band: string, created: string): Record<string, unknown> {
  return {
    id,
    job_id: `job-${id}`,
    job_reference: id.toUpperCase(),
    status: 'OPEN',
    value_band: band,
    needs_platform_admin: band !== 'STANDARD',
    created_at: created,
  };
}

function highValue(id: string, band: 'HIGH' | 'VERY_HIGH'): Record<string, unknown> {
  return {
    id,
    reference: id.toUpperCase(),
    status: 'CONFIRMED',
    value_band: band,
    is_high_value: true,
    business_name: `Business ${id}`,
    pickup_area: 'A',
    destination_area: 'B',
    created_at: '2026-10-01T08:00:00Z',
    last_changed_at: '2026-10-01T08:00:00Z',
    declared_value_kes: 200_000_000,
    needs_platform_admin: band === 'VERY_HIGH',
    operator_name: null,
  };
}

function signInAs(roles: string[]): void {
  meMock.mockResolvedValue({
    id: 'a1', phone: '+254700000001', display_name: 'Admin', locale: 'en', status: 'ACTIVE', roles, is_admin: true,
  });
}

describe('AdminControlPage (Increment 9b, P3 §19.1)', () => {
  beforeEach(() => {
    meMock.mockReset();
    disputeQueue.mockReset();
    highValueQueue.mockReset();
    signInAs(['PLATFORM_ADMIN']);
  });

  it('lists only what needs a Platform Administrator, oldest first', async () => {
    disputeQueue.mockResolvedValue(
      page([
        dispute('std111', 'STANDARD', '2026-10-01T08:00:00Z'),
        dispute('new222', 'HIGH', '2026-10-03T08:00:00Z'),
        dispute('old333', 'ELEVATED', '2026-10-02T08:00:00Z'),
      ]),
    );
    highValueQueue.mockResolvedValue(page([highValue('hi444', 'HIGH'), highValue('vh555', 'VERY_HIGH')]));

    renderWithProviders(<AdminControlPage />);

    expect(await screen.findByRole('heading', { name: 'Control' })).toBeInTheDocument();
    const disputeLinks = screen
      .getAllByRole('link')
      .filter((a) => a.getAttribute('href')?.startsWith('/disputes/'))
      .map((a) => a.getAttribute('href'));
    expect(disputeLinks).toEqual(['/disputes/old333', '/disputes/new222']);
    expect(screen.queryByText(/STD111/)).not.toBeInTheDocument();
    expect(screen.getByText(/VH555/)).toBeInTheDocument();
    expect(screen.queryByText(/HI444/)).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Open the Operations overview' })).toHaveAttribute('href', '/ops');
  });

  it('says nothing is waiting when both queues are clear', async () => {
    disputeQueue.mockResolvedValue(page([dispute('std111', 'STANDARD', '2026-10-01T08:00:00Z')]));
    highValueQueue.mockResolvedValue(page([highValue('hi444', 'HIGH')]));

    renderWithProviders(<AdminControlPage />);

    expect(await screen.findByText('Nothing is waiting for a Platform Administrator')).toBeInTheDocument();
  });

  it('does not claim all clear when a queue has more pages', async () => {
    disputeQueue.mockResolvedValue(page([], 'next-page'));
    highValueQueue.mockResolvedValue(page([]));

    renderWithProviders(<AdminControlPage />);

    expect(await screen.findByText('0+ in this list')).toBeInTheDocument();
    expect(screen.queryByText('Nothing is waiting for a Platform Administrator')).not.toBeInTheDocument();
  });

  it('shows an error with retry when a queue fails to load', async () => {
    disputeQueue.mockRejectedValue(new Error('boom'));
    highValueQueue.mockResolvedValue(page([]));

    renderWithProviders(<AdminControlPage />);

    expect(await screen.findByRole('button', { name: 'Try again' })).toBeInTheDocument();
  });

  it('sends an Operations Officer home instead of showing Control', async () => {
    signInAs(['OPERATIONS_OFFICER']);
    disputeQueue.mockResolvedValue(page([]));
    highValueQueue.mockResolvedValue(page([]));

    renderWithProviders(
      <Routes>
        <Route
          path="/admin"
          element={
            <RequirePlatformAdmin>
              <AdminControlPage />
            </RequirePlatformAdmin>
          }
        />
        <Route path="/home" element={<p>home page</p>} />
      </Routes>,
      { route: '/admin' },
    );

    expect(await screen.findByText('home page')).toBeInTheDocument();
  });
});
