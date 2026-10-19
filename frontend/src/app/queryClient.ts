import { MutationCache, QueryClient } from '@tanstack/react-query';

import { ApiError } from '@/services/problem';

export function createQueryClient(): QueryClient {
  const client: QueryClient = new QueryClient({
    // A job action refused with 412 `stale_job` means someone else changed the
    // job since this screen loaded it (ADR-2D-44). Refresh every job view so
    // the person sees what changed; the action's own error message says so.
    mutationCache: new MutationCache({
      onError: (error) => {
        if (error instanceof ApiError && error.code === 'stale_job') {
          void client.invalidateQueries({ queryKey: ['jobs'] });
          void client.invalidateQueries({ queryKey: ['disputes'] });
        }
      },
    }),
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        gcTime: 5 * 60_000,
        refetchOnWindowFocus: false,
        retry: (failureCount, error) => {
          // Never retry auth / authorization / validation failures.
          if (error instanceof ApiError && error.status > 0 && error.status < 500) return false;
          return failureCount < 2;
        },
      },
      mutations: { retry: false },
    },
  });
  // Live progress (assessment 2026-10-20 L-1, LD-1): every screen showing a
  // job, its offers, incidents, the recipient link, messages or the Ops
  // monitor re-checks about every 10 s while the tab is visible, and at once
  // when the person comes back to the tab or the device reconnects, so
  // nobody has to refresh to see where a job stands. Background tabs don't
  // poll. A refresh never touches what someone is typing (drafts are local).
  for (const prefix of LIVE_QUERY_PREFIXES) client.setQueryDefaults(prefix, LIVE_QUERY_OPTIONS);
  return client;
}

export const LIVE_REFRESH_MS = 10_000;

export const LIVE_QUERY_OPTIONS = {
  staleTime: 0,
  refetchInterval: LIVE_REFRESH_MS,
  refetchIntervalInBackground: false,
  refetchOnWindowFocus: true,
  refetchOnReconnect: true,
} as const;

export const LIVE_QUERY_PREFIXES: readonly (readonly string[])[] = [
  ['jobs'],
  ['negotiation'],
  ['disputes'],
  ['disputes-detail'],
  ['incidents'],
  ['job-events'],
  ['recipient'],
  ['messages'],
  ['ops', 'monitor'],
];
