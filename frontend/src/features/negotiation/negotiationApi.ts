import { apiRequest } from '@/services/apiClient';

import type { AcceptBody, CounterBody, DeclineBody, NegotiationThread, ProposeBody } from './types';

export const negotiationApi = {
  listThreads: (jobId: string) =>
    apiRequest<{ data: NegotiationThread[] }>(`/jobs/${jobId}/negotiation/threads`),
  propose: (jobId: string, body: ProposeBody, idempotencyKey: string) =>
    apiRequest<NegotiationThread>(`/jobs/${jobId}/negotiation/threads`, {
      method: 'POST',
      body,
      idempotencyKey,
    }),
  getThread: (threadId: string) =>
    apiRequest<NegotiationThread>(`/negotiation/threads/${threadId}`),
  counter: (threadId: string, body: CounterBody, idempotencyKey: string) =>
    apiRequest<NegotiationThread>(`/negotiation/threads/${threadId}/counter`, {
      method: 'POST',
      body,
      idempotencyKey,
    }),
  accept: (threadId: string, body: AcceptBody, idempotencyKey: string) =>
    apiRequest<NegotiationThread>(`/negotiation/threads/${threadId}/accept`, {
      method: 'POST',
      body,
      idempotencyKey,
    }),
  decline: (threadId: string, body: DeclineBody, idempotencyKey: string) =>
    apiRequest<NegotiationThread>(`/negotiation/threads/${threadId}/decline`, {
      method: 'POST',
      body,
      idempotencyKey,
    }),
};
