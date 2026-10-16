import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { Card } from '@/components/Card';
import { formatKes } from '@/features/jobs/money';

import { statementsApi, statementsQueryKey } from './statementsApi';

/**
 * "Earnings for this Job" (P3 §7.4): agreed price − commission = net, on a
 * completed job, linking to the statement once it is billed. Only the job's
 * payee (and staff) get an answer; for anyone else, such as a group's
 * driver, the server says 404 and the card stays hidden.
 */
export function JobEarningsCard({ jobId }: { jobId: string }): JSX.Element | null {
  const { t } = useTranslation('statements');
  const earnings = useQuery({
    queryKey: [...statementsQueryKey, 'earnings', jobId],
    queryFn: () => statementsApi.jobEarnings(jobId),
    retry: false,
  });
  if (!earnings.data) return null;
  const e = earnings.data;
  return (
    <Card>
      <h2 className="text-label text-fg-secondary">{t('earnings.title')}</h2>
      <dl className="mt-2 space-y-1 text-body">
        <div className="flex justify-between gap-3">
          <dt className="text-fg-muted">{t('earnings.agreed')}</dt>
          <dd className="fk-numeric text-fg">{formatKes(e.agreed_price_kes)}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-fg-muted">{t('earnings.commission')}</dt>
          <dd className="fk-numeric text-fg">− {formatKes(e.effective_commission_kes)}</dd>
        </div>
        <div className="flex justify-between gap-3 border-t border-line pt-1">
          <dt className="text-fg">{t('earnings.net')}</dt>
          <dd className="fk-numeric font-semibold text-fg">{formatKes(e.net_to_operator_kes)}</dd>
        </div>
      </dl>
      <p className="mt-2 text-body-sm text-fg-secondary">
        {e.statement ? (
          <>
            {t('earnings.onStatement')}{' '}
            <Link
              to={`/statements/${e.statement.id}`}
              className="fk-numeric text-action-secondary-text underline"
            >
              {e.statement.reference}
            </Link>
          </>
        ) : (
          t('earnings.notYetBilled')
        )}
      </p>
    </Card>
  );
}
