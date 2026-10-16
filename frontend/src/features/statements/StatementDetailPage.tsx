import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ErrorState } from '@/components/ErrorState';
import { PageLoader } from '@/components/PageLoader';
import { StatusBadge } from '@/components/StatusBadge';
import { cn } from '@/components/cn';
import { formatKes } from '@/features/jobs/money';
import { formatDate } from '@/services/datetime';
import { localizeError } from '@/services/errorMessage';

import { periodLabel, stateBadge } from './statementFormat';
import { statementsApi, statementsQueryKey } from './statementsApi';
import type { StatementDetail } from './types';

/**
 * One weekly statement (P3 §6.5 / §7.5, Commission & Statements S-2): the
 * jobs billed, any credits, what has been paid and where to pay. Labelled
 * "not a tax invoice" until eTIMS exists (D-1). The paybill number shows
 * once Fikisha sets it; until then "details to follow" (D-3). Opening it
 * marks it seen (D-6). Printable: the navigation hides when printing.
 */
export function StatementDetailPage(): JSX.Element {
  const { statementId } = useParams<{ statementId: string }>();
  const { t, i18n } = useTranslation(['statements', 'common', 'errors']);
  const qc = useQueryClient();

  const statement = useQuery({
    queryKey: [...statementsQueryKey, 'detail', statementId],
    queryFn: () => statementsApi.get(statementId!),
    enabled: !!statementId,
    retry: false,
  });

  const markSeen = useMutation({
    mutationFn: () => statementsApi.markSeen(statementId!),
    onSuccess: () => void qc.invalidateQueries({ queryKey: [...statementsQueryKey, 'list'] }),
  });
  const loaded = statement.isSuccess;
  const { mutate } = markSeen;
  useEffect(() => {
    if (loaded) mutate();
  }, [loaded, mutate]);

  if (statement.isLoading) return <PageLoader />;
  if (statement.isError) {
    return (
      <ErrorState
        message={localizeError(statement.error, t)}
        error={statement.error}
        onRetry={() => void statement.refetch()}
      />
    );
  }
  const s: StatementDetail = statement.data!;
  const lang = i18n.resolvedLanguage;
  const badge = stateBadge(s);
  const jobs = s.lines.filter((l) => l.kind === 'COMMISSION');
  const credits = s.lines.filter((l) => l.kind === 'ADJUSTMENT');

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      {/* the printed copy carries the wordmark (P3 §6.5); on screen the
          top bar already does */}
      <p className="hidden text-h3 font-semibold text-action-primary print:block">
        {t('common:appName')}
      </p>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-label text-fg-secondary">{t('statements:detail.eyebrow')}</p>
          <h1 className="fk-numeric text-h1 text-fg">{s.reference}</h1>
          <p className="mt-1 text-body text-fg-secondary">{periodLabel(s, lang)}</p>
          {s.payee.name && <p className="text-body-sm text-fg-muted">{s.payee.name}</p>}
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge tone={badge.tone} label={t(`statements:state.${badge.key}`)} />
          <Button variant="secondary" className="print:hidden" onClick={() => window.print()}>
            {t('statements:detail.print')}
          </Button>
        </div>
      </div>

      <Alert tone="info">{t('statements:detail.notTaxInvoice')}</Alert>

      <Card>
        <h2 className="text-label text-fg-secondary">{t('statements:detail.summary')}</h2>
        <dl className="mt-2 space-y-1 text-body">
          <Row label={t('statements:detail.gross')} value={formatKes(s.gross_commission_kes)} />
          {s.adjustments_kes !== 0 && (
            <Row label={t('statements:detail.credits')} value={formatKes(s.adjustments_kes)} />
          )}
          <Row
            label={t('statements:detail.netDue')}
            value={formatKes(Math.max(s.net_due_kes, 0))}
            strong
          />
          {s.settled_kes !== 0 && (
            <Row label={t('statements:detail.paid')} value={formatKes(s.settled_kes)} />
          )}
          <Row
            label={t('statements:detail.outstanding')}
            value={formatKes(s.outstanding_kes)}
            strong
          />
        </dl>
        {s.net_due_kes < 0 && (
          <p className="mt-2 text-body-sm text-fg-secondary">{t('statements:detail.creditNote')}</p>
        )}
      </Card>

      {s.outstanding_kes > 0 && (
        <Card>
          <h2 className="text-label text-fg-secondary">{t('statements:detail.howToPay')}</h2>
          {s.payment.paybill_number ? (
            <dl className="mt-2 space-y-1 text-body">
              <Row label={t('statements:detail.paybill')} value={s.payment.paybill_number} />
              <Row label={t('statements:detail.account')} value={s.payment.account_reference} />
              <Row label={t('statements:detail.amount')} value={formatKes(s.outstanding_kes)} />
            </dl>
          ) : (
            <p className="mt-2 text-body text-fg">
              {t('statements:detail.detailsToFollow', { reference: s.payment.account_reference })}
            </p>
          )}
          <p className="mt-2 text-body-sm text-fg-muted">{t('statements:detail.payNote')}</p>
        </Card>
      )}

      <Card>
        <h2 className="text-label text-fg-secondary">
          {t('statements:detail.jobs', { count: jobs.length })}
        </h2>
        {jobs.length === 0 ? (
          <p className="mt-2 text-body-sm text-fg-muted">{t('statements:detail.noJobs')}</p>
        ) : (
          <div className="mt-2 overflow-x-auto">
            <table className="w-full text-body-sm">
              <thead>
                <tr className="text-left text-fg-muted">
                  <th className="py-1 pr-3 font-normal">{t('statements:detail.job')}</th>
                  <th className="py-1 pr-3 text-right font-normal">
                    {t('statements:detail.agreedPrice')}
                  </th>
                  <th className="py-1 text-right font-normal">
                    {t('statements:detail.commission')}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {jobs.map((l) => (
                  <tr key={l.id}>
                    <td className="py-2 pr-3">
                      <Link
                        to={`/jobs/${l.job_id}`}
                        className="fk-numeric text-action-secondary-text underline"
                      >
                        {l.job_reference}
                      </Link>
                    </td>
                    <td className="fk-numeric py-2 pr-3 text-right text-fg">
                      {l.agreed_price_kes != null ? formatKes(l.agreed_price_kes) : '—'}
                    </td>
                    <td className="fk-numeric py-2 text-right text-fg">
                      {formatKes(l.amount_kes)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {credits.length > 0 && (
          <div className="mt-4">
            <h3 className="text-label text-fg-secondary">
              {t('statements:detail.creditsHeading')}
            </h3>
            <ul className="mt-1 space-y-1 text-body-sm">
              {credits.map((l) => (
                <li key={l.id} className="flex justify-between gap-3">
                  <span className="text-fg-secondary">
                    {t('statements:detail.creditFor')}{' '}
                    <Link
                      to={`/jobs/${l.job_id}`}
                      className="fk-numeric text-action-secondary-text underline"
                    >
                      {l.job_reference}
                    </Link>
                  </span>
                  <span className="fk-numeric text-fg">{formatKes(l.amount_kes)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </Card>

      {s.settlements.length > 0 && (
        <Card>
          <h2 className="text-label text-fg-secondary">{t('statements:detail.payments')}</h2>
          <ul className="mt-2 space-y-2 text-body-sm">
            {s.settlements.map((p) => (
              <li key={p.id} className="flex flex-wrap justify-between gap-x-3">
                <span className={cn('text-fg', p.reversed && 'text-fg-muted line-through')}>
                  {p.kind === 'REVERSAL'
                    ? t('statements:detail.reversal', { reference: p.payment_ref })
                    : t('statements:detail.payment', {
                        reference: p.payment_ref,
                        date: formatDate(p.paid_on, lang),
                      })}
                </span>
                <span
                  className={cn('fk-numeric text-fg', p.reversed && 'text-fg-muted line-through')}
                >
                  {formatKes(p.amount_kes)}
                </span>
                {p.kind === 'REVERSAL' && p.note && (
                  <span className="basis-full text-caption text-fg-muted">{p.note}</span>
                )}
              </li>
            ))}
          </ul>
        </Card>
      )}

      <p className="text-caption text-fg-muted">
        {t('statements:detail.generated', { date: formatDate(s.generated_at, lang) })}
      </p>
    </div>
  );
}

function Row({
  label,
  value,
  strong,
}: {
  label: string;
  value: string;
  strong?: boolean;
}): JSX.Element {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-fg-muted">{label}</dt>
      <dd className={cn('fk-numeric text-fg', strong && 'font-semibold')}>{value}</dd>
    </div>
  );
}
