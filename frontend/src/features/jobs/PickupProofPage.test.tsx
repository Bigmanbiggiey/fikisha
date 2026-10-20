import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { Route, Routes } from 'react-router-dom';

import { renderWithProviders } from '@/test/renderWithProviders';

import { PickupProofPage } from './PickupProofPage';

const get = vi.fn();
const confirmPickup = vi.fn();

vi.mock('./jobsApi', () => ({
  jobsApi: {
    get: (...a: unknown[]) => get(...a),
    confirmPickup: (...a: unknown[]) => confirmPickup(...a),
  },
}));
vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: () => Promise.reject(new Error('anon')), logout: vi.fn() },
}));

beforeAll(() => {
  URL.createObjectURL = vi.fn(() => 'blob:mock');
  URL.revokeObjectURL = vi.fn();
});

function renderAtJob(): ReturnType<typeof renderWithProviders> {
  return renderWithProviders(
    <Routes>
      <Route path="/jobs/:jobId/pickup-proof" element={<PickupProofPage />} />
      <Route path="/jobs/:jobId/custody-confirmation" element={<div>Custody confirmation screen</div>} />
      <Route path="/jobs/:jobId" element={<div>Job detail screen</div>} />
    </Routes>,
    { route: '/jobs/01a0a4123456/pickup-proof' },
  );
}

function job(pickup: string[][], overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: '01a0a4123456',
    status: 'AT_PICKUP',
    value_band: 'STANDARD',
    next_allowed_statuses: ['PICKED_UP', 'FAILED'],
    custody_requirements: { pickup, delivery: [['OTP', 'SIGNATURE']] },
    custody_confirmations: { sender_in_app: false, recipient_code: false, recipient_signature: false },
    ...overrides,
  };
}

async function typeCode(user: ReturnType<typeof userEvent.setup>): Promise<void> {
  for (const cell of screen.getAllByRole('textbox', { name: /Digit/ })) await user.type(cell, '1');
}

describe('PickupProofPage (two-party pickup, assessment 2026-10-20 L-5)', () => {
  beforeEach(() => {
    get.mockReset();
    confirmPickup.mockReset().mockResolvedValue({ id: '01a0a4123456', status: 'PICKED_UP' });
  });

  it('STANDARD: any one proof completes, and the code alone is enough', async () => {
    get.mockResolvedValue(job([['OTP', 'SIGNATURE', 'PHOTO', 'IN_APP']]));
    const user = userEvent.setup();
    renderAtJob();

    expect(await screen.findByText('This pickup needs')).toBeInTheDocument();
    expect(
      screen.getByText('the code or a signature or a photo or the sender confirms in their app'),
    ).toBeInTheDocument();
    const complete = screen.getByRole('button', { name: 'Complete pickup' });
    expect(complete).toBeDisabled();
    expect(complete).toHaveClass('min-h-target-driver');

    await typeCode(user);
    expect(complete).toBeEnabled();
    await user.click(complete);
    await waitFor(() =>
      expect(confirmPickup).toHaveBeenCalledWith(
        '01a0a4123456',
        expect.objectContaining({ code: '111111' }),
        expect.any(String),
      ),
    );
    expect(await screen.findByText('Custody confirmation screen')).toBeInTheDocument();
  });

  it('STANDARD: the sender’s in-app confirmation is enough on its own', async () => {
    get.mockResolvedValue(
      job([['OTP', 'SIGNATURE', 'PHOTO', 'IN_APP']], {
        custody_confirmations: { sender_in_app: true, recipient_code: false, recipient_signature: false },
      }),
    );
    renderAtJob();
    expect(await screen.findByText('The sender has confirmed the handover in their app.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Complete pickup' })).toBeEnabled();
  });

  it('HIGH: needs the code, a signature and a photo before it opens', async () => {
    get.mockResolvedValue(job([['OTP'], ['SIGNATURE'], ['PHOTO']], { value_band: 'HIGH' }));
    const user = userEvent.setup();
    renderAtJob();

    const complete = await screen.findByRole('button', { name: 'Complete pickup' });
    await typeCode(user);
    expect(complete).toBeDisabled(); // code alone
    await user.upload(
      screen.getByLabelText('Take photo of the goods', { selector: 'input' }),
      new File(['x'], 'goods.jpg', { type: 'image/jpeg' }),
    );
    expect(complete).toBeDisabled(); // still no signature
    // The operator-only fallback is gone at every band.
    expect(screen.queryByText(/code isn't working/i)).not.toBeInTheDocument();
  });

  it('shows the server’s reason when it still refuses', async () => {
    const { ApiError } = await import('@/services/problem');
    get.mockResolvedValue(job([['OTP', 'SIGNATURE', 'PHOTO', 'IN_APP']]));
    confirmPickup.mockRejectedValue(
      new ApiError(
        {
          type: 'about:blank',
          title: 'Unprocessable',
          status: 422,
          code: 'pickup_confirmation_required',
          detail: 'Pickup still needs: the code.',
        },
        422,
        'x',
      ),
    );
    const user = userEvent.setup();
    renderAtJob();
    await screen.findByText('This pickup needs');
    await typeCode(user);
    await user.click(screen.getByRole('button', { name: 'Complete pickup' }));
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});
