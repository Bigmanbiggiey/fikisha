import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/renderWithProviders';

import { WorkListPage } from './WorkListPage';

const discover = vi.fn();

vi.mock('./jobsApi', () => ({
  jobsApi: { discover: (...a: unknown[]) => discover(...a) },
}));
vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: () => Promise.reject(new Error('anon')), logout: vi.fn() },
}));

function opportunity(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: 'op-job-1',
    status: 'REQUESTED',
    pickup_location: { address_text: 'Depot' },
    destination_location: { address_text: 'Shop' },
    cargo: { description: 'cargo', declared_value_kes: 1000, handling_flags: [] },
    proposed_price_kes: 5000,
    eligibility: { eligible: true, trust_level: 'L1', reasons: [] },
    ...overrides,
  };
}

describe('WorkListPage', () => {
  it('shows a server-computed "you can take this" marker for an eligible opportunity', async () => {
    discover.mockResolvedValue({ data: [opportunity()], page: { next_cursor: null, prev_cursor: null } });
    renderWithProviders(<WorkListPage />);

    expect(await screen.findByText('You can take this')).toBeInTheDocument();
  });

  it('shows the concrete ineligibility reason for a job the operator cannot yet take', async () => {
    discover.mockResolvedValue({
      data: [
        opportunity({
          eligibility: {
            eligible: false,
            trust_level: '',
            reasons: ['Level none — needs L2 for this value band.'],
          },
        }),
      ],
      page: { next_cursor: null, prev_cursor: null },
    });
    renderWithProviders(<WorkListPage />);

    // Never a bare "ineligible" — the concrete server-computed reason shows.
    expect(await screen.findByText('Level none — needs L2 for this value band.')).toBeInTheDocument();
  });

  it('shows the empty state when nothing matches', async () => {
    discover.mockResolvedValue({ data: [], page: { next_cursor: null, prev_cursor: null } });
    renderWithProviders(<WorkListPage />);

    expect(await screen.findByText('No matching work right now')).toBeInTheDocument();
  });
});
