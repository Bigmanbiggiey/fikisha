import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { Route, Routes } from 'react-router-dom';

import { renderWithProviders } from '@/test/renderWithProviders';
import { ApiError } from '@/services/problem';

import { RecipientConfirmPage } from './RecipientConfirmPage';

const confirm = vi.fn();

vi.mock('@/features/jobs/recipientApi', () => ({
  recipientApi: { confirm: (...a: unknown[]) => confirm(...a) },
}));
vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: () => Promise.reject(new Error('anon')), logout: vi.fn() },
}));

beforeAll(() => {
  URL.createObjectURL = vi.fn(() => 'blob:mock');
  URL.revokeObjectURL = vi.fn();
});

function renderAtToken(token: string): ReturnType<typeof renderWithProviders> {
  return renderWithProviders(
    <Routes>
      <Route path="/r/:token/confirm" element={<RecipientConfirmPage />} />
      <Route path="/r/:token" element={<div>Recipient shell</div>} />
    </Routes>,
    { route: `/r/${token}/confirm` },
  );
}

describe('RecipientConfirmPage', () => {
  beforeEach(() => {
    confirm.mockReset();
  });

  it('submit stays disabled until a name and a full 6-digit code are entered', async () => {
    const user = userEvent.setup();
    renderAtToken('tok123');

    const submit = screen.getByRole('button', { name: 'Confirm I received the goods' });
    expect(submit).toBeDisabled();

    await user.type(screen.getByLabelText(/Your name/), 'A. Recipient');
    expect(submit).toBeDisabled();

    const cells = within(screen.getByRole('group', { name: 'Delivery code' })).getAllByRole('textbox');
    for (const cell of cells) await user.type(cell, '1');
    expect(submit).toBeEnabled();
  });

  it('submits name + code, and navigates back to the shell on success', async () => {
    confirm.mockResolvedValue({ status: 'DELIVERED' });
    const user = userEvent.setup();
    renderAtToken('tok123');

    await user.type(screen.getByLabelText(/Your name/), 'A. Recipient');
    const cells = within(screen.getByRole('group', { name: 'Delivery code' })).getAllByRole('textbox');
    for (const cell of cells) await user.type(cell, '0');
    await user.click(screen.getByRole('button', { name: 'Confirm I received the goods' }));

    expect(confirm).toHaveBeenCalledWith(
      'tok123',
      { code: '000000', party_name: 'A. Recipient', signature: undefined, photos: undefined },
      expect.any(String),
    );
    expect(await screen.findByText('Recipient shell')).toBeInTheDocument();
  });

  it('a delivery_proof_incomplete rejection prompts for a photo without clearing the entered name/OTP', async () => {
    confirm.mockRejectedValue(
      new ApiError(
        {
          type: 'about:blank',
          title: 'Incomplete',
          status: 422,
          code: 'delivery_proof_incomplete',
          detail: 'The delivery proof does not meet this value band.',
        },
        422,
        'The delivery proof does not meet this value band.',
      ),
    );
    const user = userEvent.setup();
    renderAtToken('tok123');

    await user.type(screen.getByLabelText(/Your name/), 'A. Recipient');
    const cells = within(screen.getByRole('group', { name: 'Delivery code' })).getAllByRole('textbox');
    for (const cell of cells) await user.type(cell, '0');
    await user.click(screen.getByRole('button', { name: 'Confirm I received the goods' }));

    expect(
      await screen.findByText('This delivery needs a photo of the goods too — please add one below.'),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/Your name/)).toHaveValue('A. Recipient');
    expect(screen.getByLabelText('Take a photo of the goods')).toBeInTheDocument();
  });
});
