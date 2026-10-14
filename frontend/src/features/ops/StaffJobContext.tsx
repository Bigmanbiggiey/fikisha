import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';

import { StatusBadge } from '@/components/StatusBadge';
import { jobReference } from '@/features/jobs/jobHelpers';
import type { Job } from '@/features/jobs/types';

import { opsApi } from './opsApi';

/**
 * The staff variant's extra header row (Design Phase 7 P-08): the business
 * name, a value-band chip, and "High-value review pending" while a HIGH /
 * VERY_HIGH job waits for its decision. No new API: the business name comes
 * from the Ops monitor (filtered to this job's reference) and "pending" is
 * membership of the existing high-value queue.
 */
export function StaffJobContext({ job }: { job: Job }): JSX.Element {
  const { t } = useTranslation('ops');
  const ref = jobReference(job.id);

  const row = useQuery({
    queryKey: ['ops', 'monitor', { ref }],
    queryFn: () => opsApi.monitor({ ref }),
    retry: false,
    select: (page) => page.data.find((r) => r.id === job.id) ?? null,
  });
  const reviewPossible = job.is_high_value && job.status === 'CONFIRMED';
  const pending = useQuery({
    queryKey: ['ops', 'high-value'],
    queryFn: () => opsApi.highValueQueue(),
    enabled: reviewPossible,
    retry: false,
    select: (page) => page.data.some((r) => r.id === job.id),
  });

  return (
    <div className="flex flex-wrap items-center gap-2 text-body-sm">
      {row.data?.business_name && <span className="text-fg">{row.data.business_name}</span>}
      <StatusBadge tone={job.is_high_value ? 'warning' : 'neutral'} label={t(`band.${job.value_band ?? 'none'}`)} />
      {reviewPossible && pending.data && (
        <StatusBadge tone="warning" icon="flag" label={t('staff.highValuePending')} />
      )}
    </div>
  );
}
