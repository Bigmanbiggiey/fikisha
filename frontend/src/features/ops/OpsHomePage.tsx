import { useQueries, useQuery } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Card } from '@/components/Card';
import { EmptyState } from '@/components/EmptyState';
import { PageLoader } from '@/components/PageLoader';
import { StatusBadge } from '@/components/StatusBadge';
import { useOnline } from '@/design/useOnline';
import { verificationApi } from '@/features/verification/verificationApi';

import { JobReferenceJump } from './JobReferenceJump';
import { opsApi } from './opsApi';
import type { AttentionFilter, OpsJobRow } from './types';

const ATTENTION: AttentionFilter[] = ['disputed', 'stale', 'failed'];

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

  const jobMap = new Map<string, OpsJobRow>();
  for (const q of attention) for (const row of q.data?.data ?? []) jobMap.set(row.id, row);
  const jobs = ageOrder([...jobMap.values()]);
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
            {jobs.slice(0, 8).map((job) => (
              <QueueRow
                key={job.id}
                to={`/jobs/${job.id}`}
                title={`${job.reference} · ${t(`jobs:status.${job.status}`)}`}
                meta={`${job.business_name} · ${new Date(job.last_changed_at).toLocaleString()}`}
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
                meta={`${t(`incidents:detail.status.${row.status}`)} · ${new Date(row.created_at).toLocaleString()}`}
              />
            ))}
          </Queue>

          <Queue title={t('ops:overview.disputes')} count={dis.length} more={!!disputes.data?.page.next_cursor}>
            {dis.slice(0, 8).map((row) => (
              <QueueRow
                key={row.id}
                to={`/disputes/${row.id}`}
                title={`${row.job_reference} · ${t(`ops:band.${row.value_band}`)}`}
                meta={`${t(`incidents:detail.status.${row.status}`)} · ${new Date(row.created_at).toLocaleString()}`}
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
    </div>
  );
}

function Queue({
  title,
  count,
  more,
  viewAll,
  children,
}: {
  title: string;
  count: number;
  more: boolean;
  viewAll?: string;
  children: ReactNode;
}): JSX.Element {
  const { t } = useTranslation('ops');
  const headingId = `queue-${title.replace(/\W+/g, '-').toLowerCase()}`;
  return (
    <Card>
      <section aria-labelledby={headingId} className="space-y-3">
        <div className="flex items-baseline justify-between gap-2">
          <h2 id={headingId} className="text-h3 text-fg">
            {title}
          </h2>
          {viewAll && (
            <Link to={viewAll} className="text-body-sm text-action-secondary-text underline">
              {t('overview.viewAll')}
            </Link>
          )}
        </div>
        <p aria-live="polite" className="text-body-sm text-fg-muted">
          {more ? t('overview.countMore', { count }) : t('overview.count', { count })}
        </p>
        <ul className="space-y-2">{children}</ul>
      </section>
    </Card>
  );
}

function QueueRow({ to, title, meta, badge }: { to: string; title: string; meta: string; badge?: string }): JSX.Element {
  return (
    <li>
      <Link to={to} className="block rounded-md border border-line px-3 py-2 hover:bg-surface-sunken">
        <span className="flex flex-wrap items-center gap-2">
          <span className="fk-numeric text-body font-semibold text-fg">{title}</span>
          {badge && <StatusBadge tone="warning" icon="lock" label={badge} />}
        </span>
        <span className="block text-body-sm text-fg-muted">{meta}</span>
      </Link>
    </li>
  );
}
