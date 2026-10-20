import { useQueries, useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Card } from '@/components/Card';
import { EmptyState } from '@/components/EmptyState';
import { PageLoader } from '@/components/PageLoader';
import type { BadgeTone } from '@/components/StatusBadge';
import { useOnline } from '@/design/useOnline';
import { verificationApi } from '@/features/verification/verificationApi';
import { formatRelative } from '@/services/datetime';

import { JobReferenceJump } from './JobReferenceJump';
import { CancellationFlagsCard } from './CancellationFlagsCard';
import { opsApi } from './opsApi';
import { Queue, QueueRow } from './Queue';
import type { AttentionFilter, OpsJobRow } from './types';

const ATTENTION: AttentionFilter[] = ['disputed', 'stale', 'failed'];
/** Most urgent first (F-15): a dispute freezes a job, a failed job needs a
 * decision, a stale one only needs a look. */
const URGENCY: AttentionFilter[] = ['disputed', 'failed', 'stale'];
const REASON_TONE: Record<string, BadgeTone> = { disputed: 'danger', failed: 'warning', stale: 'neutral' };

function ageOrder<T extends { created_at: string }>(rows: T[]): T[] {
  return [...rows].sort((a, b) => a.created_at.localeCompare(b.created_at));
}

/**
 * §18.1 "What needs attention?" — triage, not vanity metrics: prioritised
 * queues, oldest item first, "Nothing needs attention" as a valid good
 * state. Each queue's count sits in `aria-live` so a screen reader hears a
 * change on refetch.
 */
export function OpsHomePage(): JSX.Element {
  const { t } = useTranslation(['ops', 'jobs', 'incidents']);
  const online = useOnline();

  const attention = useQueries({
    queries: ATTENTION.map((a) => ({
      queryKey: ['ops', 'monitor', { attention: a }],
      queryFn: () => opsApi.monitor({ attention: a }),
      retry: false,
    })),
  });
  const highValue = useQuery({ queryKey: ['ops', 'high-value'], queryFn: () => opsApi.highValueQueue(), retry: false });
  const incidents = useQuery({ queryKey: ['ops', 'incidents'], queryFn: opsApi.incidentQueue, retry: false });
  const disputes = useQuery({ queryKey: ['ops', 'disputes'], queryFn: opsApi.disputeQueue, retry: false });
  const verification = useQuery({ queryKey: ['verification-queue'], queryFn: verificationApi.queue, retry: false });

  const loading =
    attention.some((q) => q.isLoading) || highValue.isLoading || incidents.isLoading || disputes.isLoading;
  if (loading) return <PageLoader />;

  // Each job once, under its most urgent reason; then most urgent first, and
  // within a reason the longest-waiting (oldest last change) first.
  const jobMap = new Map<string, { row: OpsJobRow; reason: AttentionFilter }>();
  attention.forEach((q, i) => {
    const reason = ATTENTION[i]!;
    for (const row of q.data?.data ?? []) {
      const seen = jobMap.get(row.id);
      if (!seen || URGENCY.indexOf(reason) < URGENCY.indexOf(seen.reason)) jobMap.set(row.id, { row, reason });
    }
  });
  const jobs = [...jobMap.values()].sort(
    (a, b) =>
      URGENCY.indexOf(a.reason) - URGENCY.indexOf(b.reason) ||
      a.row.last_changed_at.localeCompare(b.row.last_changed_at),
  );
  const jobsMore = attention.some((q) => q.data?.page.next_cursor);

  const hv = ageOrder(highValue.data?.data ?? []);
  const inc = ageOrder(incidents.data?.data ?? []);
  const dis = ageOrder(disputes.data?.data ?? []);
  const verificationCount = verification.data?.data.length ?? 0;
  const allClear = jobs.length + hv.length + inc.length + dis.length + verificationCount === 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-h1 text-fg">{t('ops:overview.title')}</h1>
        <p className="mt-1 text-body-sm text-fg-muted">{t('ops:overview.subtitle')}</p>
      </div>

      {!online && <Alert tone="warning">{t('ops:overview.reconnect')}</Alert>}

      <Card>
        <JobReferenceJump />
      </Card>

      {allClear ? (
        <EmptyState title={t('ops:overview.nothing')} description={t('ops:overview.nothingHint')} />
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Queue
            title={t('ops:overview.jobsNeedingAttention')}
            count={jobs.length}
            more={jobsMore}
            viewAll="/ops/jobs"
          >
            {jobs.slice(0, 8).map(({ row: job, reason }) => (
              <QueueRow
                key={job.id}
                to={`/jobs/${job.id}`}
                title={`${job.reference} · ${t(`jobs:status.${job.status}`)}`}
                meta={`${job.business_name} · ${formatRelative(job.last_changed_at)}`}
                reason={{ label: t(`ops:monitor.attentionOption.${reason}`), tone: REASON_TONE[reason] ?? 'neutral' }}
              />
            ))}
          </Queue>

          <Queue
            title={t('ops:overview.highValuePending')}
            count={hv.length}
            more={!!highValue.data?.page.next_cursor}
            viewAll="/ops/high-value"
          >
            {hv.slice(0, 8).map((row) => (
              <QueueRow
                key={row.id}
                to="/ops/high-value"
                title={`${row.reference} · ${t(`ops:band.${row.value_band ?? 'none'}`)}`}
                meta={row.business_name}
                badge={row.needs_platform_admin ? t('ops:overview.needsPlatformAdmin') : undefined}
              />
            ))}
          </Queue>

          <Queue title={t('ops:overview.openIncidents')} count={inc.length} more={!!incidents.data?.page.next_cursor}>
            {inc.slice(0, 8).map((row) => (
              <QueueRow
                key={row.id}
                to={`/incidents/${row.id}`}
                title={`${row.job_reference} · ${t(`incidents:report.type.${row.type}`)}`}
                meta={`${t(`incidents:detail.status.${row.status}`)} · ${formatRelative(row.created_at)}`}
              />
            ))}
          </Queue>

          <Queue title={t('ops:overview.disputes')} count={dis.length} more={!!disputes.data?.page.next_cursor}>
            {dis.slice(0, 8).map((row) => (
              <QueueRow
                key={row.id}
                to={`/disputes/${row.id}`}
                title={`${row.job_reference} · ${t(`ops:band.${row.value_band}`)}`}
                meta={`${t(`incidents:detail.status.${row.status}`)} · ${formatRelative(row.created_at)}`}
                badge={row.needs_platform_admin ? t('ops:overview.needsPlatformAdmin') : undefined}
              />
            ))}
          </Queue>

          <Queue title={t('ops:overview.verification')} count={verificationCount} more={!!verification.data?.page.next_cursor}>
            <li>
              <Link to="/verification" className="text-body-sm text-action-secondary-text underline">
                {t('ops:overview.openVerification')}
              </Link>
            </li>
          </Queue>
        </div>
      )}

      <CancellationFlagsCard />
    </div>
  );
}
