import { screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/renderWithProviders';

import { OpsHomePage } from './OpsHomePage';

const monitor = vi.fn();
const empty = { data: [], page: { next_cursor: null, prev_cursor: null } };

vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: () => Promise.reject(new Error('anon')), logout: vi.fn() },
}));
vi.mock('./opsApi', () => ({
  opsApi: {
    monitor: (...a: unknown[]) => monitor(...a),
    highValueQueue: () => Promise.resolve(empty),
    incidentQueue: () => Promise.resolve(empty),
    disputeQueue: () => Promise.resolve(empty),
  },
}));
vi.mock('@/features/verification/verificationApi', () => ({
  verificationApi: { queue: () => Promise.resolve(empty) },
}));

function job(id: string, status: string, lastChanged: string): Record<string, unknown> {
  return {
    id,
    reference: id.toUpperCase(),
    status,
    value_band: 'STANDARD',
    is_high_value: false,
    business_name: 'Kitengela Traders',
    pickup_area: 'A',
    destination_area: 'B',
    created_at: lastChanged,
    last_changed_at: lastChanged,
  };
}

describe('OpsHomePage — jobs needing attention (F-15)', () => {
  beforeEach(() => {
    monitor.mockReset();
    monitor.mockImplementation(({ attention }: { attention: string }) => {
      const rows: Record<string, unknown[]> = {
        disputed: [job('dis111', 'DISPUTED', '2026-10-14T05:00:00Z')],
        // also stale, but its dispute is the more urgent reason
        stale: [
          job('dis111', 'DISPUTED', '2026-10-14T05:00:00Z'),
          job('new222', 'ASSIGNED', '2026-10-13T08:00:00Z'),
          job('old333', 'ASSIGNED', '2026-10-12T08:00:00Z'),
        ],
        failed: [job('fai444', 'FAILED', '2026-10-14T06:00:00Z')],
      };
      return Promise.resolve({ data: rows[attention] ?? [], page: { next_cursor: null, prev_cursor: null } });
    });
  });

  it('shows each job once, with its reason, most urgent first then longest waiting', async () => {
    renderWithProviders(<OpsHomePage />);
    const queue = (await screen.findByRole('heading', { name: 'Jobs needing attention' })).closest('section')!;
    const rows = within(queue).getAllByRole('link').filter((a) => a.getAttribute('href')?.startsWith('/jobs/'));
    expect(rows.map((a) => a.getAttribute('href'))).toEqual([
      '/jobs/dis111',
      '/jobs/fai444',
      '/jobs/old333',
      '/jobs/new222',
    ]);
    expect(within(rows[0]!).getByText('Under dispute')).toBeInTheDocument();
    expect(within(rows[1]!).getByText("Couldn't complete")).toBeInTheDocument();
    expect(within(rows[2]!).getByText('No change for 24 hours+')).toBeInTheDocument();
  });
});
