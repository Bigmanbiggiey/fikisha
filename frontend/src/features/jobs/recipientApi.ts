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
  // `confirm`/`reportIssue` build FormData — the backend accepts optional
  // signature/photo(s) files on both, handled directly via `request.FILES`
  // rather than the JSON serializer (`apiClient` auto-detects FormData and
  // skips JSON-stringifying + the Content-Type header for it).
  confirm: (token: string, body: RecipientConfirmBody, idempotencyKey: string) => {
    const form = new FormData();
    form.append('code', body.code);
    form.append('party_name', body.party_name);
    if (body.signature) form.append('signature', body.signature);
    for (const photo of body.photos ?? []) form.append('photos', photo);
    return apiRequest<{ status: string }>(`/r/${token}/confirm`, {
      method: 'POST',
      body: form,
      auth: false,
      idempotencyKey,
    });
  },
  reportIssue: (token: string, body: RecipientReportIssueBody) => {
    const form = new FormData();
    form.append('category', body.category);
    if (body.description) form.append('description', body.description);
    if (body.other_label) form.append('other_label', body.other_label);
    for (const photo of body.photos ?? []) form.append('photos', photo);
    return apiRequest<{ report_id: string; category: string }>(`/r/${token}/report-issue`, {
      method: 'POST',
      body: form,
      auth: false,
    });
  },
};
