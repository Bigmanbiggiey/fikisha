import type { TFunction } from 'i18next';

import { ApiError } from './problem';

/**
 * Resolve an error to a localized, user-facing string. The backend's stable
 * machine `code` (e.g. `otp.invalid`, `auth.token_expired`) maps to a key in
 * the `errors` namespace; anything unrecognized falls back to `problem.detail`,
 * then a generic line.
 *
 * A missing-key check must use `defaultValue`, not `translated !== key` — for
 * a namespace-prefixed key (`errors:foo`), i18next's un-translated fallback
 * is the key *without* its namespace prefix ("foo"), which never equals the
 * prefixed `key` variable ("errors:foo") — so that comparison was always
 * true and every unregistered code silently rendered its raw machine code
 * (e.g. "vehicle_not_eligible") instead of falling through to
 * `problem.detail`. Found while wiring the Assign screen's guard-failure
 * codes (Design Phase 6 Increment 4), none of which had `errors.json`
 * entries yet.
 */
export function localizeError(error: unknown, t: TFunction): string {
  if (error instanceof ApiError) {
    const translated = t(`errors:${error.code}`, { defaultValue: '' });
    if (translated) return translated;
    if (error.problem?.detail) return error.problem.detail;
  }
  return t('errors:generic');
}
