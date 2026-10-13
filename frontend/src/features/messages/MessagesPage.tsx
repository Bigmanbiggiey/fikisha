import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { Button } from '@/components/Button';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { PageLoader } from '@/components/PageLoader';
import { cn } from '@/components/cn';
import { useAuth } from '@/features/auth/useAuth';
import { localizeError } from '@/services/errorMessage';

import { messageLines } from './messageText';
import { messagesApi, messagesQueryKey } from './messagesApi';
import { relativeAge } from './relativeAge';
import type { MessageItem, MessageKind } from './types';

const FILTERS: Record<string, MessageKind[] | null> = {
  all: null,
  offers: ['OFFER'],
  updates: ['FIKISHA_UPDATE'],
  issues: ['INCIDENT', 'DISPUTE'],
};

/**
 * Messages (Design Phase 7 sub-increment 10g; IA §5 Business "Messages").
 * One list of the conversations that already exist on the person's jobs:
 * offer threads, updates from Fikisha, and issues (incidents, disputes).
 * Newest first, unread marked. Each row opens the screen the conversation
 * lives on and marks it read. No new chat: negotiation stays the record of
 * offers, WhatsApp stays a notification channel.
 */
export function MessagesPage(): JSX.Element {
  const { t, i18n } = useTranslation(['messages', 'incidents', 'errors']);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { user } = useAuth();
  const [filter, setFilter] = useState<keyof typeof FILTERS>('all');

  const list = useInfiniteQuery({
    queryKey: [...messagesQueryKey, 'list', user?.id],
    queryFn: ({ pageParam }) => messagesApi.list(pageParam),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.page.next_cursor,
    retry: false,
  });

  const markRead = useMutation({
    mutationFn: (key: string) => messagesApi.markRead(key),
    onSuccess: () => void qc.invalidateQueries({ queryKey: messagesQueryKey }),
  });

  function open(item: MessageItem): void {
    if (item.unread) markRead.mutate(item.conversation_key);
    navigate(item.link);
  }

  if (list.isLoading) return <PageLoader />;
  if (list.isError) {
    return <ErrorState message={localizeError(list.error, t)} onRetry={() => void list.refetch()} />;
  }

  const items = (list.data?.pages ?? []).flatMap((p) => p.data);
  const kinds = FILTERS[filter];
  const shown = kinds ? items.filter((i) => kinds.includes(i.kind)) : items;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-h1 text-fg">{t('messages:title')}</h1>
        <p className="mt-1 text-body-sm text-fg-secondary">{t('messages:intro')}</p>
      </div>

      <div className="flex flex-wrap gap-2" role="group" aria-label={t('messages:filterLabel')}>
        {Object.keys(FILTERS).map((key) => (
          <button
            key={key}
            type="button"
            aria-pressed={filter === key}
            onClick={() => setFilter(key)}
            className={cn(
              'min-h-target rounded-md border px-3 text-body',
              filter === key
                ? 'border-action-primary bg-surface-brand-tint font-semibold text-action-primary'
                : 'border-line-strong bg-surface-card text-fg-secondary',
            )}
          >
            {t(`messages:filter.${key}`)}
          </button>
        ))}
      </div>

      {shown.length === 0 ? (
        <EmptyState title={t(items.length === 0 ? 'messages:empty' : 'messages:emptyFiltered')} />
      ) : (
        <ul className="divide-y divide-line rounded-md border border-line bg-surface-card">
          {shown.map((item) => {
            const { title, body } = messageLines(item, t);
            return (
              <li key={item.conversation_key}>
                <button
                  type="button"
                  onClick={() => open(item)}
                  className="flex min-h-target-driver w-full items-start gap-3 px-4 py-3 text-left hover:bg-surface-brand-tint"
                >
                  <span
                    aria-hidden
                    className={cn(
                      'mt-2 h-2.5 w-2.5 shrink-0 rounded-full',
                      item.unread ? 'bg-action-primary' : 'bg-transparent',
                    )}
                  />
                  <span className="min-w-0 flex-1">
                    <span className="flex items-baseline justify-between gap-3">
                      <span className={cn('text-body text-fg', item.unread && 'font-semibold')}>{title}</span>
                      <span className="shrink-0 text-caption text-fg-muted">
                        {relativeAge(item.at, i18n.resolvedLanguage ?? 'en')}
                      </span>
                    </span>
                    <span className="mt-0.5 block text-body-sm text-fg-secondary">{body}</span>
                    {item.unread && <span className="sr-only">{t('messages:unread')}</span>}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}

      {list.hasNextPage && (
        <Button variant="secondary" fullWidth loading={list.isFetchingNextPage} onClick={() => void list.fetchNextPage()}>
          {t('messages:loadMore')}
        </Button>
      )}
    </div>
  );
}
