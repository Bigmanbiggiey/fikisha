import { apiRequest } from '@/services/apiClient';

import type { RecipientConfirmBody, RecipientReportIssueBody, RecipientView } from './types';

/** The `/r/<token>` routes authenticate via the link token in the URL, not a
 * bearer session — every call here goes through with `auth: false` (no
 * `Authorization` header, no refresh-on-401 attempt). They live under the
 * same `/api/v1/` prefix as everything else (`fikisha.api.urls` includes
 * `jobs.api.urls` there); `phase-2d-api.md` §2 previously said "outside
 * /api/v1/" — that was wrong, corrected alongside this file. */
export const recipientApi = {
  view: (token: string) => apiRequest<RecipientView>(`/r/${token}`, { auth: false }),
  confirm: (token: string, body: RecipientConfirmBody) =>
    apiRequest<{ status: string }>(`/r/${token}/confirm`, {
      method: 'POST',
      body,
      auth: false,
    }),
  reportIssue: (token: string, body: RecipientReportIssueBody) =>
    apiRequest<{ report_id: string; category: string }>(`/r/${token}/report-issue`, {
      method: 'POST',
      body,
      auth: false,
    }),
};
