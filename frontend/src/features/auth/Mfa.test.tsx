import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiRequest } from '@/services/apiClient';
import { renderWithProviders } from '@/test/renderWithProviders';

import { MfaPage } from './MfaPage';
import { RequireAuth } from './RequireAuth';
import { StepUpProvider } from './StepUpProvider';

const meMock = vi.fn();
const api = { mfaEnroll: vi.fn(), mfaEnrollConfirm: vi.fn(), mfaVerify: vi.fn(), stepUp: vi.fn() };

vi.mock('./authApi', () => ({
  authApi: {
    me: (...a: unknown[]) => meMock(...a),
    logout: vi.fn(),
    mfaEnroll: (...a: unknown[]) => api.mfaEnroll(...a),
    mfaEnrollConfirm: (...a: unknown[]) => api.mfaEnrollConfirm(...a),
    mfaVerify: (...a: unknown[]) => api.mfaVerify(...a),
    stepUp: (...a: unknown[]) => api.stepUp(...a),
  },
}));

function admin(mfa: { enrolled: boolean; verified: boolean }) {
  return {
    id: 'a1', phone: '+254700000009', display_name: 'Admin', locale: 'en', status: 'ACTIVE',
    roles: ['PLATFORM_ADMIN'], is_admin: true,
    mfa: { required: true, step_up_fresh: false, ...mfa },
  };
}

beforeEach(() => {
  meMock.mockReset();
  for (const fn of Object.values(api)) fn.mockReset();
});

describe('admin MFA gate (Increment 9a)', () => {
  it('shows the MFA screen instead of the app until this session passes MFA', async () => {
    meMock.mockResolvedValue(admin({ enrolled: true, verified: false }));
    renderWithProviders(
      <RequireAuth>
        <p>admin console</p>
      </RequireAuth>,
    );
    expect(await screen.findByRole('heading', { name: 'Enter your authenticator code' })).toBeInTheDocument();
    expect(screen.queryByText('admin console')).not.toBeInTheDocument();
  });

  it('lets the app through once verified', async () => {
    meMock.mockResolvedValue(admin({ enrolled: true, verified: true }));
    renderWithProviders(
      <RequireAuth>
        <p>admin console</p>
      </RequireAuth>,
    );
    expect(await screen.findByText('admin console')).toBeInTheDocument();
  });

  it('enrols: QR and setup key, first code, then backup codes once', async () => {
    meMock.mockResolvedValue(admin({ enrolled: false, verified: false }));
    api.mfaEnroll.mockResolvedValue({ secret: 'JBSWY3DPEHPK3PXP', otpauth_uri: 'otpauth://totp/Fikisha:%2B2547?secret=JBSWY3DPEHPK3PXP&issuer=Fikisha' });
    api.mfaEnrollConfirm.mockResolvedValue({ backup_codes: ['ABCDE-FGHJK', 'LMNPQ-RSTUV'] });
    renderWithProviders(<MfaPage />);

    await userEvent.click(await screen.findByRole('button', { name: 'Show the QR code' }));
    expect(await screen.findByRole('img', { name: /QR code/ })).toBeInTheDocument();
    expect(screen.getByText('JBSW Y3DP EHPK 3PXP')).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText('6-digit code from the app'), '123456');
    await userEvent.click(screen.getByRole('button', { name: 'Confirm' }));
    expect(api.mfaEnrollConfirm).toHaveBeenCalledWith('123456');
    expect(await screen.findByText('ABCDE-FGHJK')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: "I've saved them, continue" })).toBeInTheDocument();
  });
});

describe('step-up prompt', () => {
  it('asks for a code on step_up_required and retries the request', async () => {
    meMock.mockResolvedValue(admin({ enrolled: true, verified: true }));
    api.stepUp.mockResolvedValue({ method: 'totp', fresh_for_seconds: 300 });
    let calls = 0;
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => {
      calls += 1;
      return calls === 1
        ? new Response(JSON.stringify({ code: 'step_up_required', status: 403, title: 'Forbidden', detail: '' }), {
            status: 403,
            headers: { 'Content-Type': 'application/problem+json' },
          })
        : new Response(JSON.stringify({ ok: true }), { status: 201, headers: { 'Content-Type': 'application/json' } });
    });
    renderWithProviders(
      <StepUpProvider>
        <p>page</p>
      </StepUpProvider>,
    );
    await screen.findByText('page');

    const result = apiRequest('/admin/config', { method: 'POST', body: {} });
    await userEvent.type(await screen.findByLabelText('Authenticator code'), '654321');
    await userEvent.click(screen.getByRole('button', { name: 'Confirm' }));

    await expect(result).resolves.toEqual({ ok: true });
    expect(api.stepUp).toHaveBeenCalledWith('654321');
    await waitFor(() => expect(calls).toBe(2));
  });
});
