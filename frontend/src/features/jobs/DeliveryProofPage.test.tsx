import { screen, waitFor } from '@testing-library/react';
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

function renderAtJob(): ReturnType<typeof renderWithProviders> {
  return renderWithProviders(
    <Routes>
      <Route path="/jobs/:jobId/delivery-proof" element={<DeliveryProofPage />} />
      <Route path="/jobs/:jobId" element={<div>Job detail screen</div>} />
    </Routes>,
    { route: '/jobs/01a0a4123456/delivery-proof' },
  );
}

function job(delivery: string[][], overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: '01a0a4123456',
    status: 'AT_DESTINATION',
    value_band: 'STANDARD',
    next_allowed_statuses: ['DELIVERED'],
    custody_requirements: { pickup: [['OTP']], delivery },
    custody_confirmations: { sender_in_app: false, recipient_code: false, recipient_signature: false },
    ...overrides,
  };
}

const photo = new File(['x'], 'pod.jpg', { type: 'image/jpeg' });

describe('DeliveryProofPage (two-party delivery, assessment 2026-10-20 L-5)', () => {
  beforeEach(() => {
    get.mockReset();
    confirmDelivery.mockReset().mockResolvedValue({ id: '01a0a4123456', status: 'DELIVERED' });
  });

  it('STANDARD: a photo alone is not enough; the code completes it', async () => {
    get.mockResolvedValue(job([['OTP', 'SIGNATURE']]));
    const user = userEvent.setup();
    renderAtJob();

    await user.type(await screen.findByLabelText(/Recipient's name/), 'A. Otieno');
    const complete = screen.getByRole('button', { name: 'Confirm delivery' });
    // No photo input at all at this band: the recipient has to take part.
    expect(screen.queryByLabelText('Take photo of the delivered goods', { selector: 'input' })).toBeNull();
    expect(complete).toBeDisabled();

    for (const cell of screen.getAllByRole('textbox', { name: /Digit/ })) await user.type(cell, '1');
    expect(complete).toBeEnabled();
    await user.click(complete);
    await waitFor(() =>
      expect(confirmDelivery).toHaveBeenCalledWith(
        '01a0a4123456',
        expect.objectContaining({ party_name: 'A. Otieno', code: '111111' }),
        expect.any(String),
      ),
    );
  });

  it('ELEVATED: the code and the driver’s photo are both needed', async () => {
    get.mockResolvedValue(job([['OTP'], ['PHOTO']], { value_band: 'ELEVATED' }));
    const user = userEvent.setup();
    renderAtJob();

    await user.type(await screen.findByLabelText(/Recipient's name/), 'A. Otieno');
    for (const cell of screen.getAllByRole('textbox', { name: /Digit/ })) await user.type(cell, '1');
    const complete = screen.getByRole('button', { name: 'Confirm delivery' });
    expect(complete).toBeDisabled();
    await user.upload(screen.getByLabelText('Take photo of the delivered goods', { selector: 'input' }), photo);
    expect(complete).toBeEnabled();
  });

  it('counts the code the recipient already gave through their link', async () => {
    get.mockResolvedValue(
      job([['OTP', 'SIGNATURE']], {
        custody_confirmations: { sender_in_app: false, recipient_code: true, recipient_signature: false },
      }),
    );
    const user = userEvent.setup();
    renderAtJob();
    expect(await screen.findByText('The recipient has confirmed with their code.')).toBeInTheDocument();
    // No code box: it's already given.
    expect(screen.queryAllByRole('textbox', { name: /Digit/ })).toHaveLength(0);
    await user.type(screen.getByLabelText(/Recipient's name/), 'A. Otieno');
    expect(screen.getByRole('button', { name: 'Confirm delivery' })).toBeEnabled();
  });
});
