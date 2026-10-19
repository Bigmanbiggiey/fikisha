import { apiRequest } from '@/services/apiClient';

import type { StoredTier, TierProposal, TierView } from './types';

export const trustApi = {
  myTier: () => apiRequest<TierView>('/operators/me/tier'),
  tier: (operatorId: string) => apiRequest<TierView>(`/operators/${operatorId}/tier`),
  /** Platform Admin, step-up: a direct promote / demote (TD-1). */
  setTier: (operatorId: string, body: { level: StoredTier; reason: string }) =>
    apiRequest<TierView>(`/admin/operators/${operatorId}/tier`, { method: 'POST', body }),
  proposals: () => apiRequest<{ data: TierProposal[] }>('/admin/tier-proposals'),
  /** Platform Admin, step-up: confirm or reject a proposal. */
  decide: (changeId: string, body: { decision: 'CONFIRM' | 'REJECT'; reason: string }) =>
    apiRequest<TierView>(`/admin/tier-proposals/${changeId}/decision`, { method: 'POST', body }),
};
