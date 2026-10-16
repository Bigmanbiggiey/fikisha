import { cursorFrom } from '@/features/ops/opsApi';
import { apiRequest } from '@/services/apiClient';

import type {
  AdminStatementsPage,
  JobEarnings,
  PaymentInput,
  RunResult,
  StatementDetail,
  StatementsPage,
} from './types';

export const statementsApi = {
  list: (cursor?: string | null) =>
    apiRequest<StatementsPage>(
      cursor ? `/statements?cursor=${encodeURIComponent(cursor)}` : '/statements',
    ),
  get: (id: string) => apiRequest<StatementDetail>(`/statements/${id}`),
  markSeen: (id: string) => apiRequest<null>(`/statements/${id}/seen`, { method: 'POST' }),
  jobEarnings: (jobId: string) => apiRequest<JobEarnings>(`/jobs/${jobId}/earnings`),
  // ─── Staff (S-3): read for Ops and Platform Admin, act for Platform Admin.
  // Recording and reversing a payment need a fresh step-up; the API client
  // asks for the code and retries (StepUpProvider).
  adminList: (
    filters: { period_start?: string; payee_kind?: string } = {},
    cursor?: string | null,
  ) => {
    const p = new URLSearchParams();
    if (filters.period_start) p.set('period_start', filters.period_start);
    if (filters.payee_kind) p.set('payee_kind', filters.payee_kind);
    if (cursor) p.set('cursor', cursor);
    const qs = p.toString();
    return apiRequest<AdminStatementsPage>(qs ? `/admin/statements?${qs}` : '/admin/statements');
  },
  adminGet: (id: string) => apiRequest<StatementDetail>(`/admin/statements/${id}`),
  run: (periodStart?: string) =>
    apiRequest<RunResult>('/admin/statements/run', {
      method: 'POST',
      body: periodStart ? { period_start: periodStart } : {},
    }),
  recordPayment: (id: string, body: PaymentInput) =>
    apiRequest<StatementDetail>(`/admin/statements/${id}/payments`, { method: 'POST', body }),
  reversePayment: (id: string, paymentId: string, reason: string) =>
    apiRequest<StatementDetail>(`/admin/statements/${id}/payments/${paymentId}/reverse`, {
      method: 'POST',
      body: { reason },
    }),
};

/** Shared by the Statements list, the Home card and the detail page. */
export const statementsQueryKey = ['statements'] as const;

export { cursorFrom };
