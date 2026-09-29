import { apiRequest } from '@/services/apiClient';

import type { MessagesPage } from './types';

export const messagesApi = {
  list: (cursor?: string | null) =>
    apiRequest<MessagesPage>(cursor ? `/messages?cursor=${encodeURIComponent(cursor)}` : '/messages'),
  markRead: (conversationKey: string) =>
    apiRequest<null>('/messages/read', { method: 'POST', body: { conversation_key: conversationKey } }),
};

/** Shared by the Messages page and the navigation badge. */
export const messagesQueryKey = ['messages'] as const;
