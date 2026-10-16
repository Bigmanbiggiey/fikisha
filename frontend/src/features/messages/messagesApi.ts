import { apiRequest } from '@/services/apiClient';

import type { MessageKind, MessagesPage } from './types';

export const messagesApi = {
  /** `kinds` filters server-side, before paging (PR #5 follow-up 3). */
  list: (cursor?: string | null, kinds?: readonly MessageKind[] | null) => {
    const p = new URLSearchParams();
    if (kinds?.length) p.set('kind', kinds.join(','));
    if (cursor) p.set('cursor', cursor);
    const qs = p.toString();
    return apiRequest<MessagesPage>(qs ? `/messages?${qs}` : '/messages');
  },
  markRead: (conversationKey: string) =>
    apiRequest<null>('/messages/read', { method: 'POST', body: { conversation_key: conversationKey } }),
};

/** Shared by the Messages page and the navigation badge. */
export const messagesQueryKey = ['messages'] as const;
