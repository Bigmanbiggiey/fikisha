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
  return client;
}
