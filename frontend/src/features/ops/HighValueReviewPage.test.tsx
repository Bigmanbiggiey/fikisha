import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/renderWithProviders';

import { HighValueReviewPage } from './HighValueReviewPage';

const meMock = vi.fn();
const highValueQueue = vi.fn();
const decideHighValue = vi.fn();

vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: (...a: unknown[]) => meMock(...a), logout: vi.fn() },
}));
vi.mock('./opsApi', () => ({
  opsApi: {
    highValueQueue: (...a: unknown[]) => highValueQueue(...a),
    decideHighValue: (...a: unknown[]) => decideHighValue(...a),
  },
}));

function row(id: string, band: 'HIGH' | 'VERY_HIGH'): Record<string, unknown> {
  return {
    id,
    reference: id.slice(-6).toUpperCase(),
    status: 'CONFIRMED',
    value_band: band,
    is_high_value: true,
    business_name: 'Kitengela Traders',
    pickup_area: 'A',
    destination_area: 'B',
    created_at: '2026-09-23T08:00:00Z',
    last_changed_at: '2026-09-23T08:00:00Z',
    declared_value_kes: band === 'HIGH' ? 50_000_000 : 200_000_000,
    needs_platform_admin: band === 'VERY_HIGH',
    operator_name: 'D. Kamau',
  };
}

function signInAs(roles: string[]): void {
  meMock.mockResolvedValue({
    id: 's1', phone: '+254700000008', display_name: 'Ops', locale: 'en', status: 'ACTIVE', roles, is_admin: true,
  });
}

describe('HighValueReviewPage', () => {
  beforeEach(() => {
    meMock.mockReset();
    highValueQueue.mockReset();
    decideHighValue.mockReset();
    highValueQueue.mockResolvedValue({
      data: [row('job-aaa111', 'HIGH'), row('job-bbb222', 'VERY_HIGH')],
      page: { next_cursor: null, prev_cursor: null },
    });
  });

  it('lets an Ops Officer decide HIGH but hides the control on VERY_HIGH', async () => {
    signInAs(['OPERATIONS_OFFICER']);
    renderWithProviders(<HighValueReviewPage />);
    expect(await screen.findByText('AAA111')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'Review this job' })).toHaveLength(1);
    expect(screen.getByText('A Platform Administrator decides this one')).toBeInTheDocument();
  });

  it('gives a Platform Admin the control on both bands', async () => {
    signInAs(['PLATFORM_ADMIN']);
    renderWithProviders(<HighValueReviewPage />);
    await screen.findByText('BBB222');
    expect(await screen.findAllByRole('button', { name: 'Review this job' })).toHaveLength(2);
  });

  it('requires a reason and warns that a rejection is permanent', async () => {
    signInAs(['OPERATIONS_OFFICER']);
    decideHighValue.mockResolvedValue({});
    const user = userEvent.setup();
    renderWithProviders(<HighValueReviewPage />);

    await user.click(await screen.findByRole('button', { name: 'Review this job' }));
    await user.click(screen.getByLabelText('Reject'));
    expect(screen.getByText(/A rejection is permanent/)).toBeInTheDocument();
    const confirm = screen.getByRole('button', { name: 'Reject permanently' });
    expect(confirm).toBeDisabled();
    await user.type(screen.getByLabelText('Reason for your decision'), 'Operator history unclear');
    await user.click(confirm);
    await waitFor(() =>
      expect(decideHighValue).toHaveBeenCalledWith('job-aaa111', 'REJECTED', 'Operator history unclear'),
    );
  });
});
