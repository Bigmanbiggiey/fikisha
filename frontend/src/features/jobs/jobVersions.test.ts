import { beforeEach, describe, expect, it, vi } from 'vitest';

import { createQueryClient } from '@/app/queryClient';
import { ApiError } from '@/services/problem';

import { forgetJobVersions, jobVersion } from './jobVersions';

const apiRequest = vi.fn();
vi.mock('@/services/apiClient', () => ({
  apiRequest: (...a: unknown[]) => apiRequest(...a),
}));

// imported after the mock so it uses it
const { jobsApi } = await import('./jobsApi');

describe('job versions and If-Match (ADR-2D-44)', () => {
  beforeEach(() => {
    apiRequest.mockReset();
    forgetJobVersions();
  });

  it('sends back the version the job was loaded at, then the one the action moved it to', async () => {
    apiRequest.mockResolvedValueOnce({ id: 'j1', status: 'CONFIRMED', version: 4 });
    await jobsApi.get('j1');
    expect(jobVersion('j1')).toBe(4);

    apiRequest.mockResolvedValueOnce({ id: 'j1', status: 'ASSIGNED', version: 5 });
    await jobsApi.assign('j1', { driver_profile_id: 'd1', vehicle_id: 'v1' }, 'key-1');
    expect(apiRequest).toHaveBeenLastCalledWith('/jobs/j1/assign', expect.objectContaining({ ifMatch: 4 }));
    expect(jobVersion('j1')).toBe(5);

    apiRequest.mockResolvedValueOnce({ id: 'j1', status: 'AT_PICKUP', version: 6 });
    await jobsApi.arrivePickup('j1', undefined, 'key-2');
    expect(apiRequest).toHaveBeenLastCalledWith(
      '/jobs/j1/custody/arrive-pickup',
      expect.objectContaining({ ifMatch: 5 }),
    );
  });

  it('sends no If-Match for a job this tab has not loaded', async () => {
    apiRequest.mockResolvedValueOnce({ id: 'j2', status: 'REQUESTED', version: 1 });
    await jobsApi.submit('j2', 'key-3');
    expect(apiRequest).toHaveBeenLastCalledWith('/jobs/j2/submit', expect.objectContaining({ ifMatch: undefined }));
  });

  it('refreshes job views when an action comes back stale_job', async () => {
    const client = createQueryClient();
    const invalidate = vi.spyOn(client, 'invalidateQueries');
    const stale = new ApiError(
      { type: 'about:blank', title: 'Precondition Failed', status: 412, code: 'stale_job', detail: 'stale' },
      412,
      'stale',
    );
    await client
      .getMutationCache()
      .build(client, { mutationFn: () => Promise.reject(stale) })
      .execute(undefined)
      .catch(() => undefined);
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['jobs'] });
  });
});
