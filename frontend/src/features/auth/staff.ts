import type { AuthUser } from './types';

/**
 * Fikisha staff = an Operations Officer or a Platform Admin, by **role**
 * (`/me.roles`), never by `is_admin` alone: the backend sets `is_admin` for
 * any active AdminProfile, so every Ops Officer has it too — reading it as
 * "Platform Admin" was a real bug (Design Phase 6 Increment 8). This is UX
 * gating only; the server's config-driven policies are the enforcement.
 */
export function isStaff(user: AuthUser | null | undefined): boolean {
  const roles = user?.roles ?? [];
  return roles.includes('OPERATIONS_OFFICER') || roles.includes('PLATFORM_ADMIN');
}

export function isPlatformAdmin(user: AuthUser | null | undefined): boolean {
  return Boolean(user?.roles.includes('PLATFORM_ADMIN'));
}
