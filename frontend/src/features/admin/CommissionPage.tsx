import { useInfiniteQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Link, useSearchParams } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { PageLoader } from '@/components/PageLoader';
import { formatKes } from '@/features/jobs/money';
import { FilterSelect } from '@/features/ops/FilterSelect';
import { localizeError } from '@/services/errorMessage';
import { formatDate } from '@/services/datetime';

import { adminApi, cursorFrom } from './adminApi';
import type { LedgerRow } from './types';

const PERIODS = ['', '7', '30', '90'] as const;

function sinceFor(days: string): string | undefined {
  if (!days) return undefined;
  return new Date(Date.now() - Number(days) * 24 * 60 * 60 * 1000).toISOString();
}

/**
 * Commission (P3 §19.4, Increment 9 D-4): the ledger of every
 * `commission_record`, its adjustments and the effective amount. Read-only.
 * There is no wallet, no balance and no pay action anywhere: Fikisha
 * records commission, and the fare moves between the parties. Weekly
 * statements, settlement and eTIMS aren't built yet; the page says so.
 */
export function CommissionPage(): JSX.Element {
  const { t } = useTranslation(['admin', 'errors']);
  const [params, setParams] = useSearchParams();
  const days = params.get('days') ?? '';
  const since = sinceFor(days);

  const ledger = useInfiniteQuery({
    queryKey: ['admin', 'commission', { days }],
    queryFn: ({ pageParam }) => adminApi.commission({ since }, pageParam),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => cursorFrom(last.page.next_cursor),
    retry: false,
  });

  const rows: LedgerRow[] = ledger.data?.pages.flatMap((p) => p.data) ?? [];
  const totals = ledger.data?.pages[0]?.totals;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-h1 text-fg">{t('admin:commission.title')}</h1>
        <p className="mt-1 text-body-sm text-fg-muted">{t('admin:commission.subtitle')}</p>
      </div>

      <Alert tone="info">{t('admin:commission.statementsNotYet')}</Alert>

      <Card className="max-w-sm">
        <FilterSelect
          id="commission-period"
          label={t('admin:commission.period')}
          value={days}
          onChange={(v) => {
            const next = new URLSearchParams(params);
            if (v) next.set('days', v);
            else next.delete('days');
            setParams(next, { replace: true });
          }}
          options={PERIODS.map((p) => [p, t(`admin:commission.periodOption.${p || 'all'}`)] as [string, string])}
        />
      </Card>

      {ledger.isLoading ? (
        <PageLoader />
      ) : ledger.isError ? (
        <ErrorState message={localizeError(ledger.error, t)} onRetry={() => void ledger.refetch()} />
      ) : (
        <>
          {totals && (
            <dl className="grid grid-cols-2 gap-3 md:grid-cols-4">
              {(
                [
                  ['records', String(totals.records)],
                  ['commission', formatKes(totals.commission_kes)],
                  ['adjustments', formatKes(totals.adjustments_kes)],
                  ['effective', formatKes(totals.effective_kes)],
                ] as const
              ).map(([key, value]) => (
                <Card key={key}>
                  <dt className="text-body-sm text-fg-muted">{t(`admin:commission.total.${key}`)}</dt>
                  <dd className="fk-numeric text-h3 text-fg">{value}</dd>
                </Card>
              ))}
            </dl>
          )}

          {rows.length === 0 ? (
            <EmptyState title={t('admin:commission.empty')} />
          ) : (
            <div className="overflow-x-auto rounded-md border border-line bg-surface-card">
              <table className="w-full border-collapse text-left text-body-sm">
                <caption className="sr-only">{t('admin:commission.title')}</caption>
                <thead>
                  <tr className="border-b border-line-strong text-fg-secondary">
                    <th scope="col" className="px-3 py-2">{t('admin:commission.col.job')}</th>
                    <th scope="col" className="px-3 py-2">{t('admin:commission.col.payee')}</th>
                    <th scope="col" className="px-3 py-2">{t('admin:commission.col.price')}</th>
                    <th scope="col" className="px-3 py-2">{t('admin:commission.col.commission')}</th>
                    <th scope="col" className="px-3 py-2">{t('admin:commission.col.adjustments')}</th>
                    <th scope="col" className="px-3 py-2">{t('admin:commission.col.effective')}</th>
                    <th scope="col" className="px-3 py-2">{t('admin:commission.col.date')}</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.id} className="border-b border-line align-top">
                      <th scope="row" className="px-3 py-2 font-semibold">
                        <Link to={`/jobs/${row.job_id}`} className="fk-numeric text-action-secondary-text underline">
                          {row.job_reference}
                        </Link>
                        <span className="block font-normal text-fg-muted">{row.business_name}</span>
                      </th>
                      <td className="px-3 py-2 text-fg">{row.payee.name ?? '—'}</td>
                      <td className="fk-numeric px-3 py-2">{formatKes(row.agreed_price_kes)}</td>
                      <td className="fk-numeric px-3 py-2">
                        {formatKes(row.commission_kes)}
                        <span className="block text-fg-muted">
                          {t('admin:commission.rule', {
                            rate: Math.round(Number(row.rate) * 10000) / 100,
                            version: row.config_version ?? '—',
                          })}
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        {row.adjustments.length === 0
                          ? '—'
                          : row.adjustments.map((a) => (
                              <span key={a.id} className="block">
                                <span className="fk-numeric">{formatKes(a.amount_kes)}</span> ·{' '}
                                {t(`admin:commission.adjustment.${a.kind}`, { defaultValue: a.kind })}
                              </span>
                            ))}
                      </td>
                      <td className="fk-numeric px-3 py-2 font-semibold">{formatKes(row.effective_kes)}</td>
                      <td className="px-3 py-2 text-fg-muted">{formatDate(row.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {ledger.hasNextPage && (
            <div className="flex justify-center">
              <Button variant="secondary" loading={ledger.isFetchingNextPage} onClick={() => void ledger.fetchNextPage()}>
                {t('admin:commission.loadMore')}
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
