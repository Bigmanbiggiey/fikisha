import { useTranslation } from 'react-i18next';

import { formatRate } from '@/features/statements/rate';

import { formatKes } from './money';
import type { FeeView } from './types';

/**
 * Fikisha's fee on a price, for one side (commission split, ADR-2D-55): the
 * business sees the fee and what it pays in total, the operator the fee and
 * what it keeps. Every amount comes from the server. `compact` drops the
 * note (offer cards); `showParty` names the side (staff see both).
 */
export function FeeLines({
  fee,
  compact = false,
  showParty = false,
}: {
  fee: FeeView;
  compact?: boolean;
  showParty?: boolean;
}): JSX.Element {
  const { t } = useTranslation('jobs');
  const business = fee.party === 'BUSINESS';
  const bottom = business ? fee.total_cost_kes : fee.operator_keeps_kes;
  return (
    <div className="text-body-sm">
      {showParty && <p className="text-label text-fg-muted">{t(`fee.party.${fee.party}`)}</p>}
      <dl className="space-y-0.5">
        <div className="flex justify-between gap-3">
          <dt className="text-fg-muted">{t('fee.fee', { rate: formatRate(fee.rate) })}</dt>
          <dd className="fk-numeric text-fg">{formatKes(fee.fee_kes)}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-fg-muted">{t(business ? 'fee.youPay' : 'fee.youKeep')}</dt>
          <dd className="fk-numeric font-semibold text-fg">{formatKes(bottom ?? 0)}</dd>
        </div>
      </dl>
      {!compact && !showParty && (
        <p className="mt-1 text-fg-secondary">
          {t(business ? 'fee.businessNote' : 'fee.operatorNote')}
        </p>
      )}
    </div>
  );
}
