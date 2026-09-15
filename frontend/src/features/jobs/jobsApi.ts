import { apiRequest } from '@/services/apiClient';

import type {
  AssignBody,
  CancellationReason,
  CommissionView,
  ConfirmDeliveryBody,
  ConfirmPickupAttestedBody,
  ConfirmPickupBusinessBody,
  ConfirmPickupOtpBody,
  FailAtPickupBody,
  GeoBody,
  Job,
  JobCreateBody,
  JobTransitionResult,
  Paged,
} from './types';

/** Every lifecycle-transition call takes an `idempotencyKey` (generate once
 * per user-initiated attempt, e.g. `crypto.randomUUID()`, and reuse it
 * across a retry of the same attempt) — the backend requires it
 * (`phase-2d-api.md` §1). */
export const jobsApi = {
  list: () => apiRequest<Paged<Job>>('/jobs'),
  create: (businessId: string, body: JobCreateBody, idempotencyKey: string) =>
    apiRequest<Job>('/jobs', {
      method: 'POST',
      body: { ...body, business_id: businessId },
      idempotencyKey,
    }),
  get: (jobId: string) => apiRequest<Job>(`/jobs/${jobId}`),

  submit: (jobId: string, idempotencyKey: string) =>
    apiRequest<JobTransitionResult>(`/jobs/${jobId}/submit`, { method: 'POST', idempotencyKey }),

  cancel: (
    jobId: string,
    body: { reason_code: CancellationReason; reason_text?: string },
    idempotencyKey: string,
  ) =>
    apiRequest<JobTransitionResult>(`/jobs/${jobId}/cancel`, {
      method: 'POST',
      body,
      idempotencyKey,
    }),

  assign: (jobId: string, body: AssignBody, idempotencyKey: string) =>
    apiRequest<JobTransitionResult>(`/jobs/${jobId}/assign`, {
      method: 'POST',
      body,
      idempotencyKey,
    }),

  commission: (jobId: string) => apiRequest<CommissionView>(`/jobs/${jobId}/commission`),

  // ─── Custody ─────────────────────────────────────────────────────────
  arrivePickup: (jobId: string, body: GeoBody, idempotencyKey: string) =>
    apiRequest<JobTransitionResult>(`/jobs/${jobId}/custody/arrive-pickup`, {
      method: 'POST',
      body,
      idempotencyKey,
    }),
  confirmPickupOtp: (jobId: string, body: ConfirmPickupOtpBody, idempotencyKey: string) =>
    apiRequest<JobTransitionResult>(`/jobs/${jobId}/custody/confirm-pickup/otp`, {
      method: 'POST',
      body,
      idempotencyKey,
    }),
  confirmPickupBusiness: (jobId: string, body: ConfirmPickupBusinessBody, idempotencyKey: string) =>
    apiRequest<JobTransitionResult>(`/jobs/${jobId}/custody/confirm-pickup/business`, {
      method: 'POST',
      body,
      idempotencyKey,
    }),
  confirmPickupAttested: (jobId: string, body: ConfirmPickupAttestedBody, idempotencyKey: string) =>
    apiRequest<JobTransitionResult>(`/jobs/${jobId}/custody/confirm-pickup/attested`, {
      method: 'POST',
      body,
      idempotencyKey,
    }),
  failAtPickup: (jobId: string, body: FailAtPickupBody, idempotencyKey: string) =>
    apiRequest<JobTransitionResult>(`/jobs/${jobId}/custody/fail-at-pickup`, {
      method: 'POST',
      body,
      idempotencyKey,
    }),
  startTransit: (jobId: string, body: GeoBody, idempotencyKey: string) =>
    apiRequest<JobTransitionResult>(`/jobs/${jobId}/custody/start-transit`, {
      method: 'POST',
      body,
      idempotencyKey,
    }),
  arriveDestination: (jobId: string, body: GeoBody, idempotencyKey: string) =>
    apiRequest<JobTransitionResult>(`/jobs/${jobId}/custody/arrive-destination`, {
      method: 'POST',
      body,
      idempotencyKey,
    }),
  confirmDelivery: (jobId: string, body: ConfirmDeliveryBody, idempotencyKey: string) =>
    apiRequest<JobTransitionResult>(`/jobs/${jobId}/custody/confirm-delivery`, {
      method: 'POST',
      body,
      idempotencyKey,
    }),
};
