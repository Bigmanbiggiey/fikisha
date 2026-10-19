import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { Card } from '@/components/Card';
import { formatKes } from '@/features/jobs/money';

import { lastWeekStart, periodLabel, weekEnd } from './statementFormat';
import { statementsApi, statementsQueryKey } from './statementsApi';

/**
 * Control (P3 §19.1): last week's statements, invoiced vs settled — the
 * pilot's collection metric (pilot-strategy §4.7). Quiet on failure: the
 * Control queues matter more than this figure.
 */
export function StatementsSummaryCard(): JSX.Element | null {
  const { t, i18n } = useTranslation('statements');
  const week = lastWeekStart();
  const summary = useQuery({
    queryKey: [...statementsQueryKey, 'admin', 'summary', week],
    queryFn: () => statementsApi.adminList({ period_start: week }),
    retry: false,
  });
  const totals = summary.data?.totals;
  if (!totals) return null;
  return (
    <Card>
      <h2 className="text-label text-fg-secondary">
        {t('admin.summaryTitle', {
          period: periodLabel(
            { period_start: week, period_end: weekEnd(week) },
            i18n.resolvedLanguage,
          ),
        })}
      </h2>
      {totals.statements === 0 ? (
        <p className="mt-2 text-body-sm text-fg-muted">{t('admin.summaryNone')}</p>
      ) : (
        <dl className="mt-2 grid grid-cols-3 gap-3">
          {(
            [
              ['invoiced', totals.invoiced_kes],
              ['settled', totals.settled_kes],
              ['outstanding', totals.outstanding_kes],
            ] as const
          ).map(([key, value]) => (
            <div key={key}>
              <dt className="text-body-sm text-fg-muted">{t(`admin.total.${key}`)}</dt>
              <dd className="fk-numeric text-h3 text-fg">{formatKes(value)}</dd>
            </div>
          ))}
        </dl>
      )}
      <Link
        to={`/ops/statements?week=${week}`}
        className="mt-2 inline-block text-body text-action-secondary-text underline"
      >
        {t('admin.summaryOpen')}
      </Link>
    </Card>
  );
}
