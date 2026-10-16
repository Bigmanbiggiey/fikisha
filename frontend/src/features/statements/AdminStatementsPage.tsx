import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useSearchParams } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { Modal } from '@/components/Modal';
import { PageLoader } from '@/components/PageLoader';
import { StatusBadge } from '@/components/StatusBadge';
import { useAuth } from '@/features/auth/useAuth';
import { isPlatformAdmin } from '@/features/auth/staff';
import { formatKes } from '@/features/jobs/money';
import { FilterSelect } from '@/features/ops/FilterSelect';
import { localizeError } from '@/services/errorMessage';

import { periodLabel, recentWeekStarts, stateBadge, weekEnd } from './statementFormat';
import { cursorFrom, statementsApi, statementsQueryKey } from './statementsApi';
import type { RunResult, StatementSummary } from './types';

const PAYEE_KINDS = ['', 'OPERATOR', 'GROUP'] as const;

/**
 * Statements, staff view (P3 §19.4, Commission & Statements S-3). Every
 * weekly statement with invoiced vs settled totals for the filter (the
 * pilot's collection metric, pilot-strategy §4.7). Operations Officers read
 * (D-4); a Platform Admin can also run a finished week by hand. Recording
 * and reversing payments is on each statement. No wallet, no pay button:
 * Fikisha records what payees paid to its paybill.
 */
export function AdminStatementsPage(): JSX.Element {
  const { t, i18n } = useTranslation(['statements', 'errors']);
  const { user } = useAuth();
  const canAct = isPlatformAdmin(user);
  const [params, setParams] = useSearchParams();
  const week = params.get('week') ?? '';
  const kind = params.get('kind') ?? '';
  const [runOpen, setRunOpen] = useState(false);
  const [ran, setRan] = useState<RunResult | null>(null);

  const list = useInfiniteQuery({
    queryKey: [...statementsQueryKey, 'admin', { week, kind }],
    queryFn: ({ pageParam }) =>
      statementsApi.adminList({ period_start: week, payee_kind: kind }, pageParam),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => cursorFrom(last.page.next_cursor),
    retry: false,
  });

  function setFilter(key: string, value: string): void {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  }

  const lang = i18n.resolvedLanguage;
  const weeks = recentWeekStarts(12);
  const rows: StatementSummary[] = list.data?.pages.flatMap((p) => p.data) ?? [];
  const totals = list.data?.pages[0]?.totals;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-h1 text-fg">{t('statements:admin.title')}</h1>
          <p className="mt-1 max-w-prose text-body-sm text-fg-muted">
            {t('statements:admin.subtitle')}
          </p>
        </div>
        {canAct && <Button onClick={() => setRunOpen(true)}>{t('statements:admin.run')}</Button>}
      </div>

      {ran && (
        <Alert tone="success">
          {t('statements:admin.ranResult', {
            count: ran.statements_created,
            period: periodLabel(ran, lang),
            skipped: ran.payees_skipped_existing,
          })}
        </Alert>
      )}

      <Card>
        <div className="grid grid-cols-1 gap-3 md:max-w-xl md:grid-cols-2">
          <FilterSelect
            id="statements-week"
            label={t('statements:admin.week')}
            value={week}
            onChange={(v) => setFilter('week', v)}
            options={[
              ['', t('statements:admin.allWeeks')] as [string, string],
              ...weeks.map(
                (w) =>
                  [w, periodLabel({ period_start: w, period_end: weekEnd(w) }, lang)] as [
                    string,
                    string,
                  ],
              ),
            ]}
          />
          <FilterSelect
            id="statements-kind"
            label={t('statements:admin.payeeKind')}
            value={kind}
            onChange={(v) => setFilter('kind', v)}
            options={PAYEE_KINDS.map(
              (k) => [k, t(`statements:admin.kind.${k || 'all'}`)] as [string, string],
            )}
          />
        </div>
      </Card>

      {list.isLoading ? (
        <PageLoader />
      ) : list.isError ? (
        <ErrorState
          message={localizeError(list.error, t)}
          error={list.error}
          onRetry={() => void list.refetch()}
        />
      ) : (
        <>
          {totals && (
            <dl className="grid grid-cols-2 gap-3 md:grid-cols-4">
              {(
                [
                  ['statements', String(totals.statements)],
                  ['invoiced', formatKes(totals.invoiced_kes)],
                  ['settled', formatKes(totals.settled_kes)],
                  ['outstanding', formatKes(totals.outstanding_kes)],
                ] as const
              ).map(([key, value]) => (
                <Card key={key}>
                  <dt className="text-body-sm text-fg-muted">
                    {t(`statements:admin.total.${key}`)}
                  </dt>
                  <dd className="fk-numeric text-h3 text-fg">{value}</dd>
                </Card>
              ))}
            </dl>
          )}

          {rows.length === 0 ? (
            <EmptyState
              title={t('statements:admin.empty')}
              description={t('statements:admin.emptyHint')}
            />
          ) : (
            <div className="overflow-x-auto rounded-md border border-line bg-surface-card">
              <table className="w-full border-collapse text-left text-body-sm">
                <caption className="sr-only">{t('statements:admin.title')}</caption>
                <thead>
                  <tr className="border-b border-line-strong text-fg-secondary">
                    <th scope="col" className="px-3 py-2">
                      {t('statements:admin.col.statement')}
                    </th>
                    <th scope="col" className="px-3 py-2">
                      {t('statements:admin.col.payee')}
                    </th>
                    <th scope="col" className="px-3 py-2">
                      {t('statements:admin.col.week')}
                    </th>
                    <th scope="col" className="px-3 py-2 text-right">
                      {t('statements:admin.col.due')}
                    </th>
                    <th scope="col" className="px-3 py-2 text-right">
                      {t('statements:admin.col.paid')}
                    </th>
                    <th scope="col" className="px-3 py-2 text-right">
                      {t('statements:admin.col.outstanding')}
                    </th>
                    <th scope="col" className="px-3 py-2">
                      {t('statements:admin.col.state')}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((s) => {
                    const badge = stateBadge(s);
                    return (
                      <tr key={s.id} className="border-b border-line align-top">
                        <th scope="row" className="px-3 py-2 font-semibold">
                          <Link
                            to={`/ops/statements/${s.id}`}
                            className="fk-numeric text-action-secondary-text underline"
                          >
                            {s.reference}
                          </Link>
                        </th>
                        <td className="px-3 py-2 text-fg">
                          {s.payee.name ?? '—'}
                          <span className="block text-fg-muted">
                            {t(`statements:admin.kind.${s.payee.kind}`)}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-fg-secondary">{periodLabel(s, lang)}</td>
                        <td className="fk-numeric px-3 py-2 text-right">
                          {formatKes(Math.max(s.net_due_kes, 0))}
                        </td>
                        <td className="fk-numeric px-3 py-2 text-right">
                          {formatKes(s.settled_kes)}
                        </td>
                        <td className="fk-numeric px-3 py-2 text-right font-semibold">
                          {formatKes(s.outstanding_kes)}
                        </td>
                        <td className="px-3 py-2">
                          <StatusBadge
                            tone={badge.tone}
                            label={t(`statements:state.${badge.key}`)}
                          />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {list.hasNextPage && (
            <div className="flex justify-center">
              <Button
                variant="secondary"
                loading={list.isFetchingNextPage}
                onClick={() => void list.fetchNextPage()}
              >
                {t('statements:loadMore')}
              </Button>
            </div>
          )}
        </>
      )}

      {canAct && (
        <RunWeekDialog
          open={runOpen}
          weeks={weeks.slice(0, 8)}
          onClose={() => setRunOpen(false)}
          onDone={(result) => {
            setRunOpen(false);
            setRan(result);
          }}
        />
      )}
    </div>
  );
}

/** Pick a finished week and run it. Idempotent server-side: anything already
 * billed is left alone, and a payee who has that week's statement is
 * skipped. */
function RunWeekDialog({
  open,
  weeks,
  onClose,
  onDone,
}: {
  open: boolean;
  weeks: string[];
  onClose: () => void;
  onDone: (result: RunResult) => void;
}): JSX.Element {
  const { t, i18n } = useTranslation(['statements', 'errors']);
  const qc = useQueryClient();
  const [week, setWeek] = useState(weeks[0] ?? '');
  const run = useMutation({
    mutationFn: () => statementsApi.run(week),
    onSuccess: (result) => {
      void qc.invalidateQueries({ queryKey: statementsQueryKey });
      onDone(result);
    },
  });
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={t('statements:admin.runTitle')}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t('statements:admin.cancel')}
          </Button>
          <Button loading={run.isPending} disabled={!week} onClick={() => run.mutate()}>
            {t('statements:admin.runConfirm')}
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        <p className="text-body text-fg-secondary">{t('statements:admin.runExplain')}</p>
        <FilterSelect
          id="run-week"
          label={t('statements:admin.week')}
          value={week}
          onChange={setWeek}
          options={weeks.map(
            (w) =>
              [
                w,
                periodLabel({ period_start: w, period_end: weekEnd(w) }, i18n.resolvedLanguage),
              ] as [string, string],
          )}
        />
        {run.isError && <Alert tone="danger">{localizeError(run.error, t)}</Alert>}
      </div>
    </Modal>
  );
}
