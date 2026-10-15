import { cursorFrom } from '@/features/ops/opsApi';
import { apiRequest } from '@/services/apiClient';

import type { JobEarnings, StatementDetail, StatementsPage } from './types';

export const statementsApi = {
  list: (cursor?: string | null) =>
    apiRequest<StatementsPage>(
      cursor ? `/statements?cursor=${encodeURIComponent(cursor)}` : '/statements',
    ),
  get: (id: string) => apiRequest<StatementDetail>(`/statements/${id}`),
  markSeen: (id: string) => apiRequest<null>(`/statements/${id}/seen`, { method: 'POST' }),
  jobEarnings: (jobId: string) => apiRequest<JobEarnings>(`/jobs/${jobId}/earnings`),
};

/** Shared by the Statements list, the Home card and the detail page. */
export const statementsQueryKey = ['statements'] as const;

export { cursorFrom };
