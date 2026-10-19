import type { Paged } from '@/features/jobs/types';
import { cursorFrom } from '@/features/ops/opsApi';
import { apiRequest } from '@/services/apiClient';

import type {
  ConfigPreview,
  ConfigView,
  DirectoryDetail,
  DirectoryKind,
  DirectoryRow,
  InterventionRequest,
  LedgerPage,
  RevealedContact,
} from './types';

function withQuery(path: string, params: URLSearchParams, cursor?: string | null): string {
  if (cursor) params.set('cursor', cursor);
  const qs = params.toString();
  return qs ? `${path}?${qs}` : path;
}

/** Platform Admin console API (Design Phase 6 Increment 9). Every endpoint
 * is Platform-Admin-only server-side; interventions and config changes
 * also need an MFA step-up the backend refuses (`step_up_required`) until
 * admin MFA exists. */
export interface UncategorisedCargo {
  description: string;
  count: number;
  last_seen: string;
}

export const adminApi = {
  /** Cargo the keyword matcher filed under Other (assessment 2026-10-19 D-5). */
  uncategorisedCargo: () => apiRequest<{ data: UncategorisedCargo[] }>('/admin/cargo-categories/uncategorised'),
  addCargoKeyword: (body: { category_code: string; keyword: string; rationale: string }) =>
    apiRequest<{ version: number }>('/admin/cargo-categories/keywords', { method: 'POST', body }),
  addCargoCategory: (body: { code: string; keywords: string[]; rationale: string }) =>
    apiRequest<{ version: number; code: string }>('/admin/cargo-categories', { method: 'POST', body }),
  directory: (kind: DirectoryKind, filters: { q?: string; state?: string } = {}, cursor?: string | null) => {
    const p = new URLSearchParams();
    if (filters.q) p.set('q', filters.q);
    if (filters.state) p.set('state', filters.state);
    return apiRequest<Paged<DirectoryRow>>(withQuery(`/admin/directory/${kind}`, p, cursor));
  },
  detail: (kind: DirectoryKind, id: string) => apiRequest<DirectoryDetail>(`/admin/directory/${kind}/${id}`),
  revealContact: (kind: DirectoryKind, id: string) =>
    apiRequest<RevealedContact>(`/admin/directory/${kind}/${id}/contact`, { method: 'POST' }),
  intervene: (body: InterventionRequest) =>
    apiRequest<{ id: string; before_state: string; after_state: string }>('/admin/interventions', {
      method: 'POST',
      body,
    }),

  config: () => apiRequest<ConfigView>('/admin/config'),
  previewConfig: (changes: Record<string, number>) =>
    apiRequest<ConfigPreview>('/admin/config/preview', { method: 'POST', body: { changes } }),
  applyConfig: (changes: Record<string, number>, rationale: string) =>
    apiRequest<{ version: number }>('/admin/config', { method: 'POST', body: { changes, rationale } }),

  commission: (filters: { since?: string; until?: string } = {}, cursor?: string | null) => {
    const p = new URLSearchParams();
    if (filters.since) p.set('since', filters.since);
    if (filters.until) p.set('until', filters.until);
    return apiRequest<LedgerPage>(withQuery('/admin/commission', p, cursor));
  },
};

export { cursorFrom };
