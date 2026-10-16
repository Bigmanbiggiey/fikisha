import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { Job } from '@/features/jobs/types';
import { renderWithProviders } from '@/test/renderWithProviders';

import { StaffJobContext } from './StaffJobContext';

const meMock = vi.fn();
const reverse = vi.fn();
const empty = { data: [], page: { next_cursor: null, prev_cursor: null } };

vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: (...a: unknown[]) => meMock(...a), logout: vi.fn() },
}));
vi.mock('./opsApi', () => ({
  opsApi: {
    monitor: () => Promise.resolve(empty),
    highValueQueue: () => Promise.resolve(empty),
    reverseHighValueRejection: (...a: unknown[]) => reverse(...a),
  },
}));

const job = {
  id: '01a1-7f3a2c', status: 'CONFIRMED', value_band: 'HIGH', is_high_value: true, high_value_decision: 'REJECTED',
} as unknown as Job;

function signInAs(roles: string[]): void {
  meMock.mockResolvedValue({
    id: 's1', phone: '+254700000009', display_name: 'Staff', locale: 'en', status: 'ACTIVE', roles, is_admin: true,
    mfa: { required: true, enrolled: true, verified: true, step_up_fresh: true },
  });
}

describe('high-value rejection reversal (founder decision 2026-10-14)', () => {
  beforeEach(() => {
    meMock.mockReset();
    reverse.mockReset();
  });

  it('lets a Platform Admin reverse a rejection with a reason', async () => {
    signInAs(['PLATFORM_ADMIN']);
    reverse.mockResolvedValue({ decision: 'APPROVED' });
    renderWithProviders(<StaffJobContext job={job} />);

    expect(screen.getByText('High-value review rejected')).toBeInTheDocument();
    await userEvent.click(await screen.findByRole('button', { name: 'Reverse the rejection' }));
    const dialog = await screen.findByRole('dialog');
    await userEvent.type(within(dialog).getByLabelText('Reason'), 'Cargo documents verified');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Continue' }));
    await userEvent.click(within(dialog).getByRole('button', { name: 'Reverse' }));
    expect(reverse).toHaveBeenCalledWith(job.id, 'Cargo documents verified');
  });

  it('shows an Operations Officer the rejection but no reversal', async () => {
    signInAs(['OPERATIONS_OFFICER']);
    renderWithProviders(<StaffJobContext job={job} />);
    expect(await screen.findByText('High-value review rejected')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Reverse the rejection' })).not.toBeInTheDocument();
  });
});
