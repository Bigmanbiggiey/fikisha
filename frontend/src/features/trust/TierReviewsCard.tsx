import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';

import { Queue, QueueRow } from '@/features/ops/Queue';
import { formatDateTime } from '@/services/datetime';

import { trustApi } from './trustApi';

/** Tier proposals waiting for a Platform Admin (operator-tiers plan T-4),
 * oldest first, each opening the operator's applicant page. */
export function TierReviewsCard(): JSX.Element | null {
  const { t } = useTranslation('trust');
  const q = useQuery({ queryKey: ['tier-proposals'], queryFn: trustApi.proposals, retry: false });
  const rows = q.data?.data ?? [];
  if (rows.length === 0) return null;
  return (
    <Queue title={t('trust:reviews.title')} count={rows.length} more={false}>
      {rows.slice(0, 8).map((p) => (
        <QueueRow
          key={p.id}
          to={`/verification/applicants/OPERATOR/${p.operator_id}`}
          title={`${p.operator_name} · ${t(`trust:level.${p.from_level}`)} → ${t(`trust:level.${p.to_level}`)}`}
          meta={formatDateTime(p.created_at)}
        />
      ))}
    </Queue>
  );
}
