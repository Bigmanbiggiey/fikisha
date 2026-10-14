export interface AuthUser {
  id: string;
  phone: string;
  display_name: string;
  locale: 'en' | 'sw';
  status: string;
  roles: string[];
  is_admin: boolean;
  /** Admin MFA state for this session (Increment 9a). Absent on old payloads. */
  mfa?: MfaStatus;
}

export interface MfaStatus {
  /** true for admin accounts only */
  required: boolean;
  /** has a confirmed authenticator */
  enrolled: boolean;
  /** this session passed MFA */
  verified: boolean;
  step_up_fresh: boolean;
}

export interface OtpRequestResult {
  challenge_id: string;
  /** Present only when the backend runs with OTP_DEV_EXPOSE (dev/test). */
  dev_code?: string;
}

export interface VerifyResult {
  access_token: string;
  access_expires_in: number;
  user: AuthUser;
}
