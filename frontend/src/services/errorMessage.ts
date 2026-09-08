import type { TFunction } from 'i18next';

import { ApiError } from './problem';

/**
 * Resolve an error to a localized, user-facing string. The backend's stable
 * machine `code` (e.g. `otp.invalid`, `auth.token_expired`) maps to a key in
 * the `errors` namespace; anything unrecognized falls back to a generic line.
 */
export function localizeError(error: unknown, t: TFunction): string {
  if (error instanceof ApiError) {
    const key = `errors:${error.code}`;
    const translated = t(key);
    if (translated !== key) return translated;
    if (error.problem?.detail) return error.problem.detail;
  }
  return t('errors:generic');
}
