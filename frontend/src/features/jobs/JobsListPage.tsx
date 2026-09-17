import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { Button } from '@/components/Button';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { JobCard } from '@/components/JobCard';
import { PageLoader } from '@/components/PageLoader';
import { localizeError } from '@/services/errorMessage';

import { jobsApi } from './jobsApi';
import { type JobSegment, jobReference, segmentFor } from './jobHelpers';
import { formatKes } from './money';

const SEGMENTS: JobSegment[] = ['active', 'requests', 'completed', 'cancelled'];

export function JobsListPage(): JSX.Element {
  const { t } = useTranslation(['jobs', 'errors']);
  const navigate = useNavigate();
  const [segment, setSegment] = useState<JobSegment>('active');

  const jobs = useQuery({ queryKey: ['jobs'], queryFn: jobsApi.list, retry: false });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-h1 text-fg">{t('jobs:list.title')}</h1>
        <Button size="compact" onClick={() => navigate('/jobs/new')}>
          {t('jobs:list.newJob')}
        </Button>
      </div>

      <div role="tablist" aria-label={t('jobs:list.title')} className="flex flex-wrap gap-1 border-b border-line">
        {SEGMENTS.map((s) => (
          <button
            key={s}
            type="button"
            role="tab"
            aria-selected={segment === s}
            onClick={() => setSegment(s)}
            className={`rounded-t-md px-3 py-2 text-body-sm ${
              segment === s
                ? 'border-b-2 border-action-primary font-semibold text-action-primary-hover'
                : 'text-fg-secondary hover:text-fg'
            }`}
          >
            {t(`jobs:list.segments.${s}`)}
          </button>
        ))}
      </div>

      {jobs.isLoading ? (
        <PageLoader />
      ) : jobs.isError ? (
        <ErrorState message={localizeError(jobs.error, t)} onRetry={() => void jobs.refetch()} />
      ) : (
        (() => {
          const rows = (jobs.data?.data ?? []).filter((j) => segmentFor(j.status) === segment);
          if (rows.length === 0) {
            return <EmptyState title={t(`jobs:list.empty${capitalize(segment)}`)} />;
          }
          return (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {rows.map((job) => (
                <JobCard
                  key={job.id}
                  reference={jobReference(job.id)}
                  state={job.status}
                  stateLabel={t(`jobs:status.${job.status}`)}
                  route={{
                    from: job.pickup_location?.address_text || '—',
                    to: job.destination_location?.address_text || '—',
                  }}
                  cargo={job.cargo?.description ?? ''}
                  price={
                    job.agreed_price_kes != null
                      ? formatKes(job.agreed_price_kes)
                      : job.proposed_price_kes != null
                        ? formatKes(job.proposed_price_kes)
                        : undefined
                  }
                  onClick={() => navigate(`/jobs/${job.id}`)}
                />
              ))}
            </div>
          );
        })()
      )}
    </div>
  );
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
