import { useQuery } from '@tanstack/react-query';

import { useAuth } from '@/features/auth/useAuth';

import { messagesApi, messagesQueryKey } from './messagesApi';

/** Unread conversations for the navigation badge (0 when off or unknown).
 * No polling: it refreshes when the window regains focus and after a
 * conversation is marked read (P1 §19: the inbox is not something people
 * must watch constantly). */
export function useUnreadMessages(enabled: boolean): number {
  const { user } = useAuth();
  const query = useQuery({
    // keyed by user: a sign-out doesn't clear the query cache, so the next
    // person on the device must not see this one's count
    queryKey: [...messagesQueryKey, 'unread', user?.id],
    queryFn: () => messagesApi.list(),
    enabled,
    staleTime: 60_000,
    retry: false,
    select: (page) => page.unread_count,
  });
  return enabled ? (query.data ?? 0) : 0;
}
