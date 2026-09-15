import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/renderWithProviders';

import { BusinessHomePage } from './BusinessHomePage';

const list = vi.fn();

vi.mock('./jobsApi', () => ({
  jobsApi: { list: (...a: unknown[]) => list(...a) },
}));
// AuthProvider calls authApi.me() on mount — keep it anonymous & quiet (this
// page doesn't itself depend on auth state, only on the mocked jobsApi).
vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: () => Promise.reject(new Error('anon')), logout: vi.fn() },
}));

function job(overrides: Record<string, unknown>): Record<string, unknown> {
  return {
    id: '01a0a4' + Math.random().toString(16).slice(2, 8),
    status: 'CONFIRMED',
    pickup_location: { address_text: 'Depot, Kitengela' },
    destination_location: { address_text: 'Shop 4, Kitengela' },
    cargo: { description: '20 cartons', declared_value_kes: 1_200_000, handling_flags: [] },
    agreed_price_kes: 250_000,
    proposed_price_kes: null,
    ...overrides,
  };
}

describe('BusinessHomePage', () => {
  it('splits jobs into needs-attention, active, and recent', async () => {
    list.mockResolvedValue({
      data: [
        job({ id: 'neg1', status: 'NEGOTIATING' }),
        job({ id: 'conf1', status: 'CONFIRMED' }),
        job({ id: 'done1', status: 'COMPLETED' }),
      ],
      page: { next_cursor: null, prev_cursor: null },
    });

    renderWithProviders(<BusinessHomePage />);

    expect(await screen.findByText(/Needs your action \(1\)/)).toBeInTheDocument();
    expect(screen.getByText('NEG1')).toBeInTheDocument(); // needs-attention row
    expect(screen.getByText('CONF1')).toBeInTheDocument(); // active JobCard
    expect(screen.getByText('Recent')).toBeInTheDocument();
  });

  it('shows the empty state when there are no active deliveries', async () => {
    list.mockResolvedValue({ data: [], page: { next_cursor: null, prev_cursor: null } });
    renderWithProviders(<BusinessHomePage />);
    expect(await screen.findByText('No deliveries in progress')).toBeInTheDocument();
  });
});
