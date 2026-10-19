import { QueryClientProvider, useQuery } from '@tanstack/react-query';
import { act, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { createQueryClient, LIVE_REFRESH_MS } from './queryClient';

describe('live progress (assessment 2026-10-20 L-1)', () => {
  afterEach(() => vi.useRealTimers());

  it('re-checks job, negotiation and recipient data but not reference data', () => {
    const client = createQueryClient();
    for (const key of [['jobs', 'j1'], ['negotiation', 'threads', 'j1'], ['recipient', 't'], ['ops', 'monitor', {}]]) {
      expect(client.getQueryDefaults(key).refetchInterval).toBe(LIVE_REFRESH_MS);
    }
    expect(client.getQueryDefaults(['reference', 'cargoCategories']).refetchInterval).toBeUndefined();
    expect(client.getQueryDefaults(['vehicles', 'u1']).refetchInterval).toBeUndefined();
  });

  it('shows a new job status without a reload', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const fetchJob = vi.fn().mockResolvedValueOnce({ status: 'ASSIGNED' }).mockResolvedValue({ status: 'PICKED_UP' });
    function Status(): JSX.Element {
      const q = useQuery({ queryKey: ['jobs', 'j1'], queryFn: fetchJob });
      return <p>{q.data?.status ?? 'loading'}</p>;
    }
    render(
      <QueryClientProvider client={createQueryClient()}>
        <Status />
      </QueryClientProvider>,
    );
    expect(await screen.findByText('ASSIGNED')).toBeInTheDocument();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(LIVE_REFRESH_MS + 100);
    });
    expect(await screen.findByText('PICKED_UP')).toBeInTheDocument();
  });
});
