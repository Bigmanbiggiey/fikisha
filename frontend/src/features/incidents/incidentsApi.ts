import { apiRequest } from '@/services/apiClient';

import type {
  AddStatementBody,
  Dispute,
  Escalation,
  EscalateBody,
  EvidenceAttachResult,
  Incident,
  OpenDisputeBody,
  ReportIncidentBody,
  ResolveDisputeBody,
  Statement,
} from './types';

export const incidentsApi = {
  listIncidents: (jobId: string) =>
    apiRequest<{ data: Incident[] }>(`/jobs/${jobId}/incidents`),
  reportIncident: (jobId: string, body: ReportIncidentBody, idempotencyKey: string) =>
    apiRequest<Incident>(`/jobs/${jobId}/incidents`, { method: 'POST', body, idempotencyKey }),
  getIncident: (incidentId: string) => apiRequest<Incident>(`/incidents/${incidentId}`),

  attachEvidence: (incidentId: string, file: File, caption?: string) => {
    const form = new FormData();
    form.append('file', file);
    if (caption) form.append('caption', caption);
    return apiRequest<EvidenceAttachResult>(`/incidents/${incidentId}/evidence`, {
      method: 'POST',
      body: form,
    });
  },
  addStatement: (incidentId: string, body: AddStatementBody) =>
    apiRequest<Statement>(`/incidents/${incidentId}/statements`, { method: 'POST', body }),
  startReview: (incidentId: string) =>
    apiRequest<Incident>(`/incidents/${incidentId}/review`, { method: 'POST' }),
  startAmicable: (incidentId: string) =>
    apiRequest<Incident>(`/incidents/${incidentId}/amicable`, { method: 'POST' }),
  escalate: (incidentId: string, body: EscalateBody) =>
    apiRequest<Escalation>(`/incidents/${incidentId}/escalate`, { method: 'POST', body }),

  listDisputes: (jobId: string) => apiRequest<{ data: Dispute[] }>(`/jobs/${jobId}/disputes`),
  openDispute: (jobId: string, body: OpenDisputeBody, idempotencyKey: string) =>
    apiRequest<Dispute>(`/jobs/${jobId}/disputes`, { method: 'POST', body, idempotencyKey }),
  getDispute: (disputeId: string) => apiRequest<Dispute>(`/disputes/${disputeId}`),
  resolveDispute: (disputeId: string, body: ResolveDisputeBody, idempotencyKey: string) =>
    apiRequest<Dispute>(`/disputes/${disputeId}/resolve`, {
      method: 'POST',
      body,
      idempotencyKey,
    }),
};
