import type { Paged } from '@/features/jobs/types';
import { apiRequest } from '@/services/apiClient';

import type {
  AuditEntryRow,
  AuditFilters,
  DisputeQueueRow,
  HighValueDecision,
  HighValueRow,
  IncidentQueueRow,
  JobEventRow,
  JobNote,
  MonitorFilters,
  OpsJobRow,
  RevealedContacts,
} from './types';

export const notesQueryKey = (jobId: string) => ['job-notes', jobId] as const;

/** `next_cursor` comes back as a full link — pull out just the cursor
 * value so it can be re-sent against the same path. */
export function cursorFrom(link: string | null): string | null {
  if (!link) return null;
  try {
    return new URL(link, 'http://x').searchParams.get('cursor');
  } catch {
    return null;
  }
}

function withQuery(path: string, params: URLSearchParams, cursor?: string | null): string {
  if (cursor) params.set('cursor', cursor);
  const qs = params.toString();
  return qs ? `${path}?${qs}` : path;
}

export const opsApi = {
  monitor: (filters: MonitorFilters = {}, cursor?: string | null) => {
    const p = new URLSearchParams();
    if (filters.status && filters.status.length) p.set('status', filters.status.join(','));
    if (filters.value_band) p.set('value_band', filters.value_band);
    if (filters.ref) p.set('ref', filters.ref);
    if (filters.attention) p.set('attention', filters.attention);
    if (filters.stale_hours) p.set('stale_hours', String(filters.stale_hours));
    return apiRequest<Paged<OpsJobRow>>(withQuery('/ops/jobs', p, cursor));
  },
  highValueQueue: (cursor?: string | null) =>
    apiRequest<Paged<HighValueRow>>(withQuery('/ops/high-value', new URLSearchParams(), cursor)),
  decideHighValue: (jobId: string, decision: HighValueDecision, rationale: string) =>
    apiRequest<unknown>(`/jobs/${jobId}/high-value-decision`, {
      method: 'POST',
      body: { decision, rationale },
    }),
  incidentQueue: () => apiRequest<Paged<IncidentQueueRow>>('/ops/incidents'),
  disputeQueue: () => apiRequest<Paged<DisputeQueueRow>>('/ops/disputes'),

  notes: (jobId: string) => apiRequest<{ data: JobNote[] }>(`/jobs/${jobId}/notes`),
  addNote: (jobId: string, text: string) =>
    apiRequest<JobNote>(`/jobs/${jobId}/notes`, { method: 'POST', body: { text } }),
  events: (jobId: string) => apiRequest<{ data: JobEventRow[] }>(`/jobs/${jobId}/events`),
  revealContacts: (jobId: string) =>
    apiRequest<RevealedContacts>(`/jobs/${jobId}/contacts/reveal`, { method: 'POST' }),

  audit: (filters: AuditFilters = {}, cursor?: string | null) => {
    const p = new URLSearchParams();
    for (const [k, v] of Object.entries(filters)) if (v) p.set(k, v);
    return apiRequest<Paged<AuditEntryRow>>(withQuery('/audit/entries', p, cursor));
  },
};
