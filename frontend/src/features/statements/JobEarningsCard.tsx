import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { Card } from '@/components/Card';
import { formatKes } from '@/features/jobs/money';

import { formatRate } from './rate';
import { statementsApi, statementsQueryKey } from './statementsApi';
import type { CommissionParty } from './types';

/**
 * One side's commission on a completed job, linking to the statement once it
 * is billed (commission split, ADR-2D-55):
 * - operator side, "Earnings for this job" (P3 §7.4): agreed price − fee =
 *   what the operator keeps;
 * - business side, "Cost for this job": paid to the operator + Fikisha's
 *   fee = total.
 * Only the side's payee (and staff, and a business's Dispatchers for the
 * business side) get an answer; for anyone else, such as a group's driver,
 * the server says 404 and the card stays hidden.
 */
export function JobEarningsCard({
  jobId,
  party,
}: {
  jobId: string;
  party: CommissionParty;
}): JSX.Element | null {
  const { t } = useTranslation('statements');
  const earnings = useQuery({
    queryKey: [...statementsQueryKey, 'earnings', jobId, party],
    queryFn: () => statementsApi.jobEarnings(jobId, party),
    retry: false,
  });
  if (!earnings.data) return null;
  const e = earnings.data;
  const rate = formatRate(e.rate);
  const business = e.party === 'BUSINESS';
  return (
    <Card>
      <h2 className="text-label text-fg-secondary">
        {t(business ? 'cost.title' : 'earnings.title')}
      </h2>
      <dl className="mt-2 space-y-1 text-body">
        <div className="flex justify-between gap-3">
          <dt className="text-fg-muted">{t(business ? 'cost.agreed' : 'earnings.agreed')}</dt>
          <dd className="fk-numeric text-fg">{formatKes(e.agreed_price_kes)}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-fg-muted">
            {t(business ? 'cost.fee' : 'earnings.commission', { rate })}
          </dt>
          <dd className="fk-numeric text-fg">
            {business ? '+' : '−'} {formatKes(e.effective_commission_kes)}
          </dd>
        </div>
        <div className="flex justify-between gap-3 border-t border-line pt-1">
          <dt className="text-fg">{t(business ? 'cost.total' : 'earnings.net')}</dt>
          <dd className="fk-numeric font-semibold text-fg">
            {formatKes((business ? e.total_cost_kes : e.net_to_operator_kes) ?? 0)}
          </dd>
        </div>
      </dl>
      <p className="mt-2 text-body-sm text-fg-secondary">
        {e.statement ? (
          <>
            {t(business ? 'cost.onStatement' : 'earnings.onStatement')}{' '}
            <Link
              to={`/statements/${e.statement.id}`}
              className="fk-numeric text-action-secondary-text underline"
            >
              {e.statement.reference}
            </Link>
          </>
        ) : (
          t(business ? 'cost.notYetBilled' : 'earnings.notYetBilled')
        )}
      </p>
    </Card>
  );
}
