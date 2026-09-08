import { createContext } from 'react';

import type { AuthUser, VerifyResult } from './types';

export type AuthStatus = 'loading' | 'authenticated' | 'anonymous';

export interface AuthContextValue {
  status: AuthStatus;
  user: AuthUser | null;
  /** Persist the result of a successful OTP verification. */
  completeLogin: (result: VerifyResult) => void;
  logout: () => Promise<void>;
  reloadMe: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);
