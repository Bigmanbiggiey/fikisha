import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/renderWithProviders';

import { JobsListPage } from './JobsListPage';

const list = vi.fn();

vi.mock('./jobsApi', () => ({
  jobsApi: { list: (...a: unknown[]) => list(...a) },
}));
vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: () => Promise.reject(new Error('anon')), logout: vi.fn() },
}));

describe('JobsListPage', () => {
  it('shows the Active segment by default and switches to Completed on tap', async () => {
    list.mockResolvedValue({
      data: [
        {
          id: 'active1',
          status: 'CONFIRMED',
          pickup_location: { address_text: 'Depot' },
          destination_location: { address_text: 'Shop' },
          cargo: { description: 'cargo', declared_value_kes: 1000, handling_flags: [] },
          agreed_price_kes: 5000,
          proposed_price_kes: null,
        },
        {
          id: 'donedn',
          status: 'COMPLETED',
          pickup_location: { address_text: 'Depot' },
          destination_location: { address_text: 'Shop' },
          cargo: { description: 'cargo', declared_value_kes: 1000, handling_flags: [] },
          agreed_price_kes: 5000,
          proposed_price_kes: null,
        },
      ],
      page: { next_cursor: null, prev_cursor: null },
    });

    renderWithProviders(<JobsListPage />);

    expect(await screen.findByText('CTIVE1')).toBeInTheDocument();
    expect(screen.queryByText('DONEDN')).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('tab', { name: 'Completed' }));

    expect(await screen.findByText('DONEDN')).toBeInTheDocument();
    expect(screen.queryByText('CTIVE1')).not.toBeInTheDocument();
  });

  it('shows the segment-specific empty state', async () => {
    list.mockResolvedValue({ data: [], page: { next_cursor: null, prev_cursor: null } });
    renderWithProviders(<JobsListPage />);
    expect(await screen.findByText('No active deliveries.')).toBeInTheDocument();
  });
});
