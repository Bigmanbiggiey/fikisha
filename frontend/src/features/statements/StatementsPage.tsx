import { useInfiniteQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { Button } from '@/components/Button';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { PageLoader } from '@/components/PageLoader';
import { StatusBadge } from '@/components/StatusBadge';
import { cn } from '@/components/cn';
import { useAuth } from '@/features/auth/useAuth';
import { formatKes } from '@/features/jobs/money';
import { localizeError } from '@/services/errorMessage';

import { periodLabel, stateBadge } from './statementFormat';
import { cursorFrom, statementsApi, statementsQueryKey } from './statementsApi';
import type { StatementSummary } from './types';

/**
 * Earnings / Statements (P3 §7.5 "More → Earnings / Statements", Commission &
 * Statements S-2). The weekly commission statements of the person's operator
 * profile and of the groups they own or manage, newest week first. A dot
 * marks one they haven't opened (D-6). No wallet, no balance, no pay
 * button: the payee pays Fikisha's paybill outside the app.
 */
export function StatementsPage(): JSX.Element {
  const { t, i18n } = useTranslation(['statements', 'errors']);
  const { user } = useAuth();

  const list = useInfiniteQuery({
    queryKey: [...statementsQueryKey, 'list', user?.id],
    queryFn: ({ pageParam }) => statementsApi.list(pageParam),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => cursorFrom(last.page.next_cursor),
    retry: false,
  });

  if (list.isLoading) return <PageLoader />;
  if (list.isError) {
    return (
      <ErrorState
        message={localizeError(list.error, t)}
        error={list.error}
        onRetry={() => void list.refetch()}
      />
    );
  }

  const rows: StatementSummary[] = (list.data?.pages ?? []).flatMap((p) => p.data);
  const payees = new Set(rows.map((r) => r.payee.id));

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-h1 text-fg">{t('statements:title')}</h1>
        <p className="mt-1 max-w-prose text-body-sm text-fg-secondary">{t('statements:intro')}</p>
      </div>

      {rows.length === 0 ? (
        <EmptyState title={t('statements:empty')} description={t('statements:emptyBody')} />
      ) : (
        <ul className="divide-y divide-line rounded-md border border-line bg-surface-card">
          {rows.map((s) => {
            const badge = stateBadge(s);
            const unseen = s.seen === false;
            return (
              <li key={s.id}>
                <Link
                  to={`/statements/${s.id}`}
                  className="flex min-h-target-driver items-start gap-3 px-4 py-3 hover:bg-surface-brand-tint"
                >
                  <span
                    aria-hidden
                    className={cn(
                      'mt-2 h-2.5 w-2.5 shrink-0 rounded-full',
                      unseen ? 'bg-action-primary' : 'bg-transparent',
                    )}
                  />
                  <span className="min-w-0 flex-1">
                    <span className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                      <span className={cn('text-body text-fg', unseen && 'font-semibold')}>
                        {periodLabel(s, i18n.resolvedLanguage)}
                        {unseen && <span className="sr-only"> · {t('statements:new')}</span>}
                      </span>
                      <span className="fk-numeric text-body text-fg">
                        {formatKes(Math.max(s.net_due_kes, 0))}
                      </span>
                    </span>
                    <span className="mt-1 flex flex-wrap items-center gap-2 text-caption text-fg-muted">
                      <span className="fk-numeric">{s.reference}</span>
                      {/* someone who is both an operator and a group manager
                          sees both payees' statements; name the payee */}
                      {payees.size > 1 && s.payee.name && <span>· {s.payee.name}</span>}
                      <StatusBadge tone={badge.tone} label={t(`statements:state.${badge.key}`)} />
                    </span>
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}

      {list.hasNextPage && (
        <Button
          variant="secondary"
          onClick={() => void list.fetchNextPage()}
          disabled={list.isFetchingNextPage}
        >
          {t('statements:loadMore')}
        </Button>
      )}
    </div>
  );
}
