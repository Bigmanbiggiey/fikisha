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
};
