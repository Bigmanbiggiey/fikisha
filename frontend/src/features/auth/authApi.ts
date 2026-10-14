import { apiRequest } from '@/services/apiClient';

import type { AuthUser, OtpRequestResult, VerifyResult } from './types';

export const authApi = {
  requestOtp(phone: string): Promise<OtpRequestResult> {
    return apiRequest<OtpRequestResult>('/auth/otp/request', {
      method: 'POST',
      body: { phone },
      auth: false,
    });
  },

  verifyOtp(challengeId: string, code: string): Promise<VerifyResult> {
    return apiRequest<VerifyResult>('/auth/otp/verify', {
      method: 'POST',
      body: { challenge_id: challengeId, code },
      auth: false,
    });
  },

  me(): Promise<AuthUser> {
    return apiRequest<AuthUser>('/me');
  },

  logout(): Promise<null> {
    return apiRequest<null>('/auth/logout', { method: 'POST' });
  },

  // ─── Admin MFA (Increment 9a) ────────────────────────────────────────
  mfaEnroll(): Promise<{ secret: string; otpauth_uri: string }> {
    return apiRequest('/auth/mfa/enroll', { method: 'POST' });
  },
  mfaEnrollConfirm(code: string): Promise<{ backup_codes: string[] }> {
    return apiRequest('/auth/mfa/enroll/confirm', { method: 'POST', body: { code } });
  },
  mfaVerify(code: string): Promise<{ method: string; backup_codes_left: number }> {
    return apiRequest('/auth/mfa/verify', { method: 'POST', body: { code } });
  },
  stepUp(code: string): Promise<{ method: string; fresh_for_seconds: number }> {
    // never itself trigger the step-up prompt
    return apiRequest('/auth/step-up', { method: 'POST', body: { code }, stepUp: false });
  },
};
