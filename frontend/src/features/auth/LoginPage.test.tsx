import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/renderWithProviders';

import { LoginPage } from './LoginPage';

const me = vi.fn();
const requestOtp = vi.fn();
const verifyOtp = vi.fn();

vi.mock('./authApi', () => ({
  authApi: {
    me: (...args: unknown[]) => me(...args),
    requestOtp: (...args: unknown[]) => requestOtp(...args),
    verifyOtp: (...args: unknown[]) => verifyOtp(...args),
    logout: vi.fn(),
  },
}));

describe('LoginPage', () => {
  beforeEach(() => {
    me.mockRejectedValue(new Error('anonymous'));
    requestOtp.mockReset();
    verifyOtp.mockReset();
  });

  it('walks phone -> code -> verified', async () => {
    requestOtp.mockResolvedValue({ challenge_id: 'chal-1', dev_code: '000000' });
    verifyOtp.mockResolvedValue({
      access_token: 'acc',
      access_expires_in: 900,
      user: {
        id: 'u1',
        phone: '+254700000001',
        display_name: '',
        locale: 'en',
        status: 'ACTIVE',
        roles: [],
        is_admin: false,
      },
    });

    renderWithProviders(<LoginPage />, { route: '/login' });

    await userEvent.type(screen.getByLabelText(/phone number/i), '0700000001');
    await userEvent.click(screen.getByRole('button', { name: /send code/i }));

    await waitFor(() => expect(requestOtp).toHaveBeenCalledWith('0700000001'));
    // Dev code surfaced and pre-filled.
    expect(screen.getByText(/development mode/i)).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /verify and continue/i }));

    await waitFor(() => expect(verifyOtp).toHaveBeenCalledWith('chal-1', '000000'));
  });

  it('shows a localized error when the code is rejected', async () => {
    const { ApiError } = await import('@/services/problem');
    requestOtp.mockResolvedValue({ challenge_id: 'chal-2' });
    verifyOtp.mockRejectedValue(
      new ApiError(
        { type: '', title: '', status: 401, code: 'otp.invalid', detail: 'x' },
        401,
        'x',
      ),
    );

    renderWithProviders(<LoginPage />, { route: '/login' });

    await userEvent.type(screen.getByLabelText(/phone number/i), '0700000002');
    await userEvent.click(screen.getByRole('button', { name: /send code/i }));
    await screen.findByLabelText(/one-time code/i);
    await userEvent.type(screen.getByLabelText(/one-time code/i), '999999');
    await userEvent.click(screen.getByRole('button', { name: /verify and continue/i }));

    expect(await screen.findByText(/that code is not correct/i)).toBeInTheDocument();
  });
});
