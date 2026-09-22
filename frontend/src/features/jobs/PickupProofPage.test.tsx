import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { Route, Routes } from 'react-router-dom';

import { renderWithProviders } from '@/test/renderWithProviders';

import { PickupProofPage } from './PickupProofPage';

const get = vi.fn();
const confirmPickupOtp = vi.fn();
const confirmPickupAttested = vi.fn();

vi.mock('./jobsApi', () => ({
  jobsApi: {
    get: (...a: unknown[]) => get(...a),
    confirmPickupOtp: (...a: unknown[]) => confirmPickupOtp(...a),
    confirmPickupAttested: (...a: unknown[]) => confirmPickupAttested(...a),
  },
}));
vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: () => Promise.reject(new Error('anon')), logout: vi.fn() },
}));

beforeAll(() => {
  URL.createObjectURL = vi.fn(() => 'blob:mock');
  URL.revokeObjectURL = vi.fn();
});

function renderAtJob(jobId: string): ReturnType<typeof renderWithProviders> {
  return renderWithProviders(
    <Routes>
      <Route path="/jobs/:jobId/pickup-proof" element={<PickupProofPage />} />
      <Route path="/jobs/:jobId/custody-confirmation" element={<div>Custody confirmation screen</div>} />
      <Route path="/jobs/:jobId" element={<div>Job detail screen</div>} />
    </Routes>,
    { route: `/jobs/${jobId}/pickup-proof` },
  );
}

function baseJob(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: '01a0a4123456',
    status: 'AT_PICKUP',
    value_band: 'STANDARD',
    next_allowed_statuses: ['PICKED_UP', 'FAILED'],
    ...overrides,
  };
}

describe('PickupProofPage', () => {
  beforeEach(() => {
    get.mockReset();
    confirmPickupOtp.mockReset();
    confirmPickupAttested.mockReset();
  });

  it('STANDARD: submits the operator-attested fallback with the photo and contact name', async () => {
    get.mockResolvedValue(baseJob());
    confirmPickupAttested.mockResolvedValue(baseJob({ status: 'PICKED_UP' }));
    const user = userEvent.setup();
    renderAtJob('01a0a4123456');

    await user.click(await screen.findByRole('button', { name: 'Code not working?' }));
    await user.type(screen.getByLabelText(/Pickup contact's name/), 'J. Mwangi');

    const file = new File(['goods'], 'goods.jpg', { type: 'image/jpeg' });
    await user.upload(screen.getByLabelText('Take photo of the goods', { selector: 'input' }), file);

    await user.click(screen.getByRole('button', { name: 'Confirm handover' }));

    expect(confirmPickupAttested).toHaveBeenCalledWith(
      '01a0a4123456',
      { pickup_contact_name: 'J. Mwangi', photo: file },
      expect.any(String),
    );
    expect(await screen.findByText('Custody confirmation screen')).toBeInTheDocument();
  });

  it('ELEVATED+: no fallback segment renders, and a failed OTP shows the blocking explainer', async () => {
    get.mockResolvedValue(baseJob({ value_band: 'ELEVATED' }));
    confirmPickupOtp.mockRejectedValue(new Error('wrong code'));
    const user = userEvent.setup();
    renderAtJob('01a0a4123456');

    expect(await screen.findByText('Elevated delivery — verified pickup required')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Code not working?' })).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Enter code' }));
    const cells = screen.getAllByRole('textbox');
    for (const cell of cells) await user.type(cell, '1');
    await user.click(screen.getByRole('button', { name: 'Confirm handover' }));

    expect(
      await screen.findByText(
        "This delivery needs a verified pickup. Ask the sender for the code, or ask them to confirm in the Fikisha app. Contact Fikisha support if it still can't be done.",
      ),
    ).toBeInTheDocument();
  });
});
