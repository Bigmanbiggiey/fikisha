import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Route, Routes } from 'react-router-dom';

import { renderWithProviders } from '@/test/renderWithProviders';

import { PickupConfirmPage } from './PickupConfirmPage';

const get = vi.fn();
const confirmPickupBusiness = vi.fn();

vi.mock('./jobsApi', () => ({
  jobsApi: {
    get: (...a: unknown[]) => get(...a),
    confirmPickupBusiness: (...a: unknown[]) => confirmPickupBusiness(...a),
  },
}));
vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: () => Promise.reject(new Error('anon')), logout: vi.fn() },
}));

function renderAtJob(jobId: string): ReturnType<typeof renderWithProviders> {
  return renderWithProviders(
    <Routes>
      <Route path="/jobs/:jobId/confirm-pickup" element={<PickupConfirmPage />} />
    </Routes>,
    { route: `/jobs/${jobId}/confirm-pickup` },
  );
}

describe('PickupConfirmPage', () => {
  beforeEach(() => {
    get.mockReset();
    confirmPickupBusiness.mockReset();
  });

  it('requires acknowledgement before the deliberate-tap confirm step unlocks', async () => {
    get.mockResolvedValue({
      id: 'job1',
      status: 'AT_PICKUP',
      cargo: { description: '20 cartons' },
      pickup_location: { address_text: 'Depot, Kitengela' },
    });
    const user = userEvent.setup();
    renderAtJob('job1');

    const confirmButton = await screen.findByRole('button', { name: 'Confirm pickup' });
    expect(confirmButton).toBeDisabled();

    await user.click(screen.getByRole('checkbox'));
    expect(confirmButton).toBeEnabled();

    await user.click(confirmButton);
    expect(await screen.findByText('Yes, confirm pickup for JOB1')).toBeInTheDocument();

    confirmPickupBusiness.mockResolvedValue({ id: 'job1', status: 'PICKED_UP' });
    await user.click(screen.getByRole('button', { name: 'Yes, confirm' }));

    expect(confirmPickupBusiness).toHaveBeenCalledWith('job1', {}, expect.any(String));
  });

  it('shows a read-only "moved on" state once the job leaves AT_PICKUP', async () => {
    get.mockResolvedValue({
      id: 'job1',
      status: 'PICKED_UP',
      cargo: { description: '20 cartons' },
      pickup_location: { address_text: 'Depot, Kitengela' },
    });
    renderAtJob('job1');

    expect(await screen.findByText('This job has moved on — nothing needed here.')).toBeInTheDocument();
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
  });
});
