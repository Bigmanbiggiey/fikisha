import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';

import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { JobCard } from '@/components/JobCard';
import { JobStatusChip } from '@/components/JobStatusChip';
import { PageLoader } from '@/components/PageLoader';
import { localizeError } from '@/services/errorMessage';

import { jobsApi } from './jobsApi';
import { businessNextAction, jobReference, needsBusinessAttention } from './jobHelpers';
import { formatKes } from './money';
import type { Job, JobStatus } from './types';

function statusLabel(t: (key: string) => string, status: JobStatus): string {
  return t(`jobs:status.${status}`);
}

export function BusinessHomePage(): JSX.Element {
  const { t } = useTranslation(['jobs', 'errors']);
  const navigate = useNavigate();

  const jobs = useQuery({ queryKey: ['jobs'], queryFn: jobsApi.list, retry: false });

  if (jobs.isLoading) return <PageLoader />;
  if (jobs.isError) {
    return <ErrorState message={localizeError(jobs.error, t)} onRetry={() => void jobs.refetch()} />;
  }

  const NOT_YET_ACTIVE = new Set<JobStatus>(['DRAFT', 'REQUESTED']);
  const SETTLED = new Set<JobStatus>(['COMPLETED', 'CANCELLED', 'FAILED']);

  const all = jobs.data?.data ?? [];
  const needsAttention = all.filter((j) => needsBusinessAttention(j.status));
  const active = all.filter(
    (j) => !needsBusinessAttention(j.status) && !NOT_YET_ACTIVE.has(j.status) && !SETTLED.has(j.status),
  );
  const recent = all.filter((j) => SETTLED.has(j.status)).slice(0, 5);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-h1 text-fg">{t('jobs:home.title')}</h1>
        <Button onClick={() => navigate('/jobs/new')}>{t('jobs:home.requestTransport')}</Button>
      </div>

      {needsAttention.length > 0 && (
        <section aria-labelledby="needs-action-heading">
          <h2 id="needs-action-heading" className="text-label text-fg-secondary" aria-live="polite">
            {t('jobs:home.needsAction')} ({needsAttention.length})
          </h2>
          <ul className="mt-2 space-y-2">
            {needsAttention.map((job) => (
              <li key={job.id}>
                <AttentionRow job={job} />
              </li>
            ))}
          </ul>
        </section>
      )}

      <section aria-labelledby="active-heading">
        <h2 id="active-heading" className="text-label text-fg-secondary">
          {t('jobs:home.activeDeliveries')}
        </h2>
        {active.length === 0 ? (
          <div className="mt-2">
            <EmptyState title={t('jobs:home.emptyTitle')} description={t('jobs:home.emptyBody')} />
          </div>
        ) : (
          <div className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-2">
            {active.map((job) => (
              <JobCard
                key={job.id}
                reference={jobReference(job.id)}
                state={job.status}
                stateLabel={statusLabel(t, job.status)}
                route={{
                  from: job.pickup_location?.address_text || '—',
                  to: job.destination_location?.address_text || '—',
                }}
                cargo={job.cargo?.description ?? ''}
                price={job.agreed_price_kes != null ? formatKes(job.agreed_price_kes) : undefined}
                onClick={() => navigate(`/jobs/${job.id}`)}
              />
            ))}
          </div>
        )}
      </section>

      {recent.length > 0 && (
        <section aria-labelledby="recent-heading">
          <h2 id="recent-heading" className="text-label text-fg-secondary">
            {t('jobs:home.recent')}
          </h2>
          <ul className="mt-2 space-y-1">
            {recent.map((job) => (
              <li key={job.id}>
                <Link to={`/jobs/${job.id}`} className="flex items-center gap-2 py-1 text-body-sm">
                  <JobStatusChip state={job.status} label={statusLabel(t, job.status)} />
                  <span className="text-fg">{jobReference(job.id)}</span>
                  <span className="text-fg-muted">
                    {job.destination_location?.address_text}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function AttentionRow({ job }: { job: Job }): JSX.Element {
  const { t } = useTranslation('jobs');
  const action = businessNextAction(job.status);
  return (
    <Link to={`/jobs/${job.id}`} className="block rounded-md">
      <Card interactive className="flex items-center justify-between gap-3">
        <div>
          <p className="font-semibold text-fg">{jobReference(job.id)}</p>
          <p className="text-body-sm text-fg-secondary">
            {job.destination_location?.address_text}
          </p>
        </div>
        {action && (
          <span className="text-body-sm font-medium text-action-secondary-text">
            {t(`jobs:action.${action}`)}
          </span>
        )}
      </Card>
    </Link>
  );
}
