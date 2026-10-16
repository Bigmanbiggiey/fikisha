import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/Button';
import { StatusBadge } from '@/components/StatusBadge';
import { AdminActionDialog } from '@/features/admin/AdminActionDialog';
import { isPlatformAdmin } from '@/features/auth/staff';
import { useAuth } from '@/features/auth/useAuth';
import { jobReference } from '@/features/jobs/jobHelpers';
import type { Job } from '@/features/jobs/types';

import { opsApi } from './opsApi';

/**
 * The staff variant's extra header row (Design Phase 7 P-08): the business
 * name, a value-band chip, and "High-value review pending" while a HIGH /
 * VERY_HIGH job waits for its decision. No new API: the business name comes
 * from the Ops monitor (filtered to this job's reference) and "pending" is
 * membership of the existing high-value queue.
 *
 * A rejected high-value job shows "Review rejected"; a Platform Admin can
 * reverse the rejection with a reason (founder decision 2026-10-14). The
 * server asks for a fresh MFA step-up, which the app's step-up prompt
 * handles.
 */
export function StaffJobContext({ job }: { job: Job }): JSX.Element {
  const { t } = useTranslation(['ops', 'admin']);
  const { user } = useAuth();
  const qc = useQueryClient();
  const [reversing, setReversing] = useState(false);
  const ref = jobReference(job.id);
  const reverse = useMutation({
    mutationFn: (reason: string) => opsApi.reverseHighValueRejection(job.id, reason),
    onSuccess: () => {
      setReversing(false);
      void qc.invalidateQueries({ queryKey: ['jobs', job.id] });
      void qc.invalidateQueries({ queryKey: ['ops'] });
    },
  });
  const rejected = job.high_value_decision === 'REJECTED';

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
      {rejected && <StatusBadge tone="danger" label={t('staff.highValueRejected')} />}
      {rejected && isPlatformAdmin(user) && (
        <Button variant="secondary" onClick={() => setReversing(true)}>
          {t('staff.reverseRejection')}
        </Button>
      )}
      <AdminActionDialog
        open={reversing}
        onClose={() => setReversing(false)}
        title={t('staff.reverseRejection')}
        restatement={t('staff.reverseRestate', { ref })}
        confirmLabel={t('staff.reverseConfirm')}
        destructive={false}
        pending={reverse.isPending}
        error={reverse.error}
        onConfirm={({ reason }) => reverse.mutate(reason)}
      />
    </div>
  );
}
