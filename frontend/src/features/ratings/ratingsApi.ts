import { apiRequest } from '@/services/apiClient';

import type { JobRatingsView } from './types';

export const ratingsQueryKey = (jobId: string) => ['jobs', jobId, 'ratings'] as const;

export const ratingsApi = {
  forJob: (jobId: string) => apiRequest<JobRatingsView>(`/jobs/${jobId}/ratings`),
  submit: (jobId: string, body: { score: number; comment: string }) =>
    apiRequest<JobRatingsView>(`/jobs/${jobId}/ratings`, { method: 'POST', body }),
};
