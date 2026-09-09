import { apiRequest, fetchBlob } from '@/services/apiClient';
import type { Paged } from '@/features/org/types';

export type SubjectType = 'OPERATOR' | 'VEHICLE' | 'BASE';

export interface VerificationDecisionRow {
  id: string;
  action: string;
  actor_role: string;
  reason: string;
  note: string;
  created_at: string;
}

export interface VerificationEvidenceRow {
  id: string;
  evidence_id: string;
  kind: string;
  content_type: string;
  pii_class: string;
  issued_at: string | null;
  expires_at: string | null;
  submitted_at: string;
  superseded_at: string | null;
}

export interface VerificationRecord {
  id: string;
  subject_type: SubjectType;
  subject_id: string;
  domain: string;
  state: string;
  effective_state: string;
  issuing_authority: string;
  verified_at: string | null;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
  evidence?: VerificationEvidenceRow[];
  decisions?: VerificationDecisionRow[];
}

export interface SubjectStatus {
  subject_type: SubjectType;
  subject_id: string;
  eligibility: Record<string, string>;
  requirements: { domain: string; mandatory: boolean; state: string }[];
  required_domains: string[];
}

export const EVIDENCE_KINDS = [
  'NATIONAL_ID',
  'PASSPORT',
  'SELFIE',
  'DRIVING_LICENCE',
  'GOOD_CONDUCT_CERT',
  'LOGBOOK',
  'INSPECTION_CERT',
  'INSURANCE_CERT',
  'NTSA_OPERATOR_LICENCE',
  'SPEED_LIMITER_CERT',
  'TELEMATICS_CERT',
  'OWNER_CONSENT',
  'VEHICLE_PHOTO',
  'PLATE_PHOTO',
  'BASE_PHOTO',
  'OTHER',
] as const;

export const verificationApi = {
  listRecords: () => apiRequest<Paged<VerificationRecord>>('/verification/records'),
  getRecord: (id: string) => apiRequest<VerificationRecord>(`/verification/records/${id}`),
  createRecord: (subject_type: SubjectType, subject_id: string, domain: string) =>
    apiRequest<VerificationRecord>('/verification/records', {
      method: 'POST',
      body: { subject_type, subject_id, domain },
    }),
  addEvidence: (recordId: string, file: File, kind: string) => {
    const form = new FormData();
    form.append('file', file);
    form.append('kind', kind);
    return apiRequest<VerificationRecord>(`/verification/records/${recordId}/evidence`, {
      method: 'POST',
      body: form,
    });
  },
  submit: (recordId: string) =>
    apiRequest<VerificationRecord>(`/verification/records/${recordId}/submit`, {
      method: 'POST',
      body: {},
    }),
  reviewStart: (id: string) =>
    apiRequest<VerificationRecord>(`/verification/records/${id}/review/start`, {
      method: 'POST',
      body: {},
    }),
  reviewApprove: (id: string, reason = '') =>
    apiRequest<VerificationRecord>(`/verification/records/${id}/review/approve`, {
      method: 'POST',
      body: { reason },
    }),
  reviewReject: (id: string, reason: string) =>
    apiRequest<VerificationRecord>(`/verification/records/${id}/review/reject`, {
      method: 'POST',
      body: { reason },
    }),
  reviewRequestInfo: (id: string, note: string) =>
    apiRequest<VerificationRecord>(`/verification/records/${id}/review/request-info`, {
      method: 'POST',
      body: { note },
    }),
  queue: () => apiRequest<Paged<VerificationRecord>>('/verification/queue'),
  subjectStatus: (subjectType: SubjectType, subjectId: string) =>
    apiRequest<SubjectStatus>(`/verification/subjects/${subjectType}/${subjectId}/status`),
  evidenceBlob: (evidenceId: string) =>
    fetchBlob(`/verification/evidence/${evidenceId}/content`),
};
