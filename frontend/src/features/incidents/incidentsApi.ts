import { apiRequest, fetchBlob } from '@/services/apiClient';

import type {
  Dispute,
  Incident,
  IncidentStatementItem,
  ReportIncidentBody,
  ResolveDisputeBody,
} from './types';

// `Paged` isn't used by these list endpoints (both return a plain
// `{ data: [...] }`, no cursor) — re-declared locally to avoid depending on
// `features/jobs/types.ts` for an unrelated shape.
type Listed<T> = { data: T[] };

export const incidentsApi = {
  listForJob: (jobId: string) => apiRequest<Listed<Incident>>(`/jobs/${jobId}/incidents`),
  report: (jobId: string, body: ReportIncidentBody, idempotencyKey: string) =>
    apiRequest<Incident>(`/jobs/${jobId}/incidents`, { method: 'POST', body, idempotencyKey }),
  get: (incidentId: string) => apiRequest<Incident>(`/incidents/${incidentId}`),
  // One file per call — `AttachEvidenceSerializer` takes a single `file`,
  // unlike the recipient endpoints' `photos` list.
  attachEvidence: (incidentId: string, file: File, caption?: string) => {
    const form = new FormData();
    form.append('file', file);
    if (caption) form.append('caption', caption);
    return apiRequest<{ id: string; evidence_object_id: string }>(
      `/incidents/${incidentId}/evidence`,
      { method: 'POST', body: form },
    );
  },
  evidenceBlob: (evidenceRowId: string) =>
    fetchBlob(`/incidents/evidence/${evidenceRowId}/content`),
  addStatement: (incidentId: string, text: string) =>
    apiRequest<IncidentStatementItem>(`/incidents/${incidentId}/statements`, {
      method: 'POST',
      body: { text },
    }),
  startReview: (incidentId: string) =>
    apiRequest<Incident>(`/incidents/${incidentId}/review`, { method: 'POST' }),
  startAmicable: (incidentId: string) =>
    apiRequest<Incident>(`/incidents/${incidentId}/amicable`, { method: 'POST' }),
  escalate: (incidentId: string, reason: string) =>
    apiRequest<{ id: string; incident_id: string; dispute_id: string | null; escalated_to: string }>(
      `/incidents/${incidentId}/escalate`,
      { method: 'POST', body: { reason } },
    ),
};

export const disputesApi = {
  listForJob: (jobId: string) => apiRequest<Listed<Dispute>>(`/jobs/${jobId}/disputes`),
  get: (disputeId: string) => apiRequest<Dispute>(`/disputes/${disputeId}`),
  open: (jobId: string, incidentIds: string[], idempotencyKey: string) =>
    apiRequest<{ dispute: Dispute; job: unknown }>(`/jobs/${jobId}/disputes`, {
      method: 'POST',
      body: { incident_ids: incidentIds },
      idempotencyKey,
    }),
  resolve: (disputeId: string, body: ResolveDisputeBody, idempotencyKey: string) =>
    apiRequest<{ resolution_id: string; job: unknown }>(`/disputes/${disputeId}/resolve`, {
      method: 'POST',
      body,
      idempotencyKey,
    }),
};
