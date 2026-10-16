import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { Card } from '@/components/Card';
import { cn } from '@/components/cn';
import { formatKes } from '@/features/jobs/money';
import { formatDate } from '@/services/datetime';

import type { StatementDetail, StatementSettlement } from './types';

/** Shared by the payee statement page (S-2) and the staff one (S-3). */

export function Row({
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

export function SummaryCard({
  s,
  staff = false,
}: {
  s: StatementDetail;
  staff?: boolean;
}): JSX.Element {
  const { t } = useTranslation('statements');
  return (
    <Card>
      <h2 className="text-label text-fg-secondary">{t('detail.summary')}</h2>
      <dl className="mt-2 space-y-1 text-body">
        <Row
          label={t(staff ? 'admin.gross' : 'detail.gross')}
          value={formatKes(s.gross_commission_kes)}
        />
        {s.adjustments_kes !== 0 && (
          <Row label={t('detail.credits')} value={formatKes(s.adjustments_kes)} />
        )}
        <Row label={t('detail.netDue')} value={formatKes(Math.max(s.net_due_kes, 0))} strong />
        {s.settled_kes !== 0 && <Row label={t('detail.paid')} value={formatKes(s.settled_kes)} />}
        <Row label={t('detail.outstanding')} value={formatKes(s.outstanding_kes)} strong />
      </dl>
      {s.net_due_kes < 0 && (
        <p className="mt-2 text-body-sm text-fg-secondary">{t('detail.creditNote')}</p>
      )}
    </Card>
  );
}

export function LinesCard({ s }: { s: StatementDetail }): JSX.Element {
  const { t } = useTranslation('statements');
  const jobs = s.lines.filter((l) => l.kind === 'COMMISSION');
  const credits = s.lines.filter((l) => l.kind === 'ADJUSTMENT');
  return (
    <Card>
      <h2 className="text-label text-fg-secondary">{t('detail.jobs', { count: jobs.length })}</h2>
      {jobs.length === 0 ? (
        <p className="mt-2 text-body-sm text-fg-muted">{t('detail.noJobs')}</p>
      ) : (
        <div className="mt-2 overflow-x-auto">
          <table className="w-full text-body-sm">
            <thead>
              <tr className="text-left text-fg-muted">
                <th className="py-1 pr-3 font-normal">{t('detail.job')}</th>
                <th className="py-1 pr-3 text-right font-normal">{t('detail.agreedPrice')}</th>
                <th className="py-1 text-right font-normal">{t('detail.commission')}</th>
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
                  <td className="fk-numeric py-2 text-right text-fg">{formatKes(l.amount_kes)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {credits.length > 0 && (
        <div className="mt-4">
          <h3 className="text-label text-fg-secondary">{t('detail.creditsHeading')}</h3>
          <ul className="mt-1 space-y-1 text-body-sm">
            {credits.map((l) => (
              <li key={l.id} className="flex justify-between gap-3">
                <span className="text-fg-secondary">
                  {t('detail.creditFor')}{' '}
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
  );
}

/** Payments and reversals; a reversed payment is struck through. Staff pass
 * ``action`` to put a control (Reverse) on a row. */
export function PaymentsCard({
  s,
  action,
  empty,
}: {
  s: StatementDetail;
  action?: (p: StatementSettlement) => ReactNode;
  /** shown when there are no payments; omit to hide the card instead */
  empty?: string;
}): JSX.Element | null {
  const { t, i18n } = useTranslation('statements');
  if (s.settlements.length === 0 && !empty) return null;
  return (
    <Card>
      <h2 className="text-label text-fg-secondary">{t('detail.payments')}</h2>
      {s.settlements.length === 0 ? (
        <p className="mt-2 text-body-sm text-fg-muted">{empty}</p>
      ) : (
        <ul className="mt-2 divide-y divide-line text-body-sm">
          {s.settlements.map((p) => (
            <li
              key={p.id}
              className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 py-2"
            >
              <span className={cn('min-w-0 text-fg', p.reversed && 'text-fg-muted line-through')}>
                {p.kind === 'REVERSAL'
                  ? t('detail.reversal', { reference: p.payment_ref })
                  : t('detail.payment', {
                      reference: p.payment_ref,
                      date: formatDate(p.paid_on, i18n.resolvedLanguage),
                    })}
              </span>
              <span className="flex items-center gap-3">
                <span
                  className={cn('fk-numeric text-fg', p.reversed && 'text-fg-muted line-through')}
                >
                  {formatKes(p.amount_kes)}
                </span>
                {action?.(p)}
              </span>
              {p.note && (p.kind === 'REVERSAL' || action) && (
                <span className="basis-full text-caption text-fg-muted">{p.note}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
