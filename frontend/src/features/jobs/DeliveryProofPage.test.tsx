import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { Route, Routes } from 'react-router-dom';

import { renderWithProviders } from '@/test/renderWithProviders';

import { DeliveryProofPage } from './DeliveryProofPage';

const get = vi.fn();
const confirmDelivery = vi.fn();

vi.mock('./jobsApi', () => ({
  jobsApi: {
    get: (...a: unknown[]) => get(...a),
    confirmDelivery: (...a: unknown[]) => confirmDelivery(...a),
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
      <Route path="/jobs/:jobId/delivery-proof" element={<DeliveryProofPage />} />
      <Route path="/jobs/:jobId" element={<div>Job detail screen</div>} />
    </Routes>,
    { route: `/jobs/${jobId}/delivery-proof` },
  );
}

function baseJob(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: '01a0a4123456',
    status: 'AT_DESTINATION',
    value_band: 'STANDARD',
    next_allowed_statuses: ['DELIVERED'],
    ...overrides,
  };
}

describe('DeliveryProofPage', () => {
  beforeEach(() => {
    get.mockReset();
    confirmDelivery.mockReset();
  });

  it('STANDARD: a photo alone is enough, alongside the recipient name', async () => {
    get.mockResolvedValue(baseJob());
    confirmDelivery.mockResolvedValue(baseJob({ status: 'DELIVERED' }));
    const user = userEvent.setup();
    renderAtJob('01a0a4123456');

    await user.type(await screen.findByLabelText(/Recipient's name/), 'A. Otieno');
    await user.click(screen.getByRole('button', { name: 'Photo' }));

    const file = new File(['pod'], 'pod.jpg', { type: 'image/jpeg' });
    await user.upload(
      screen.getByLabelText('Take photo of the delivered goods', { selector: 'input' }),
      file,
    );

    await user.click(screen.getByRole('button', { name: 'Confirm delivery' }));

    expect(confirmDelivery).toHaveBeenCalledWith(
      '01a0a4123456',
      { party_name: 'A. Otieno', code: undefined, photos: [file], signature: undefined },
      expect.any(String),
    );
  });

  it('ELEVATED+: OTP alone is not enough — photo is also required before submit enables', async () => {
    get.mockResolvedValue(baseJob({ value_band: 'ELEVATED' }));
    const user = userEvent.setup();
    renderAtJob('01a0a4123456');

    await user.type(await screen.findByLabelText(/Recipient's name/), 'A. Otieno');
    const otpCells = screen.getAllByRole('textbox');
    for (const cell of otpCells) await user.type(cell, '1');

    expect(screen.getByRole('button', { name: 'Confirm delivery' })).toBeDisabled();

    const file = new File(['pod'], 'pod.jpg', { type: 'image/jpeg' });
    await user.upload(
      screen.getByLabelText('Take photo of the delivered goods', { selector: 'input' }),
      file,
    );

    expect(screen.getByRole('button', { name: 'Confirm delivery' })).toBeEnabled();
  });
});
