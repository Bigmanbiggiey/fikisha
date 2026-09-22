import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';

import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { JobCard } from '@/components/JobCard';
import { PageLoader } from '@/components/PageLoader';
import { localizeError } from '@/services/errorMessage';

import { jobReference, needsOperatorAttention, operatorNextAction } from './jobHelpers';
import { jobsApi } from './jobsApi';
import { formatKes } from './money';
import type { Job } from './types';

/**
 * Operator Home (`design-phase-3-wireframes.md` §7.1) — mirrors
 * `BusinessHomePage`'s structure (current-job focus, needs-response bucket,
 * available-work count). "Earnings this week" is deferred (see
 * `jobHelpers.operatorNextAction`'s doc — no operator-facing commission read
 * exists yet).
 */
export function OperatorHomePage(): JSX.Element {
  const { t } = useTranslation(['jobs', 'errors']);
  const navigate = useNavigate();

  const jobs = useQuery({ queryKey: ['jobs'], queryFn: jobsApi.list, retry: false });
  const work = useQuery({ queryKey: ['jobs', 'opportunities', ''], queryFn: () => jobsApi.discover(), retry: false });

  if (jobs.isLoading) return <PageLoader />;
  if (jobs.isError) {
    return <ErrorState message={localizeError(jobs.error, t)} onRetry={() => void jobs.refetch()} />;
  }

  const ACTIVE = new Set(['ASSIGNED', 'AT_PICKUP', 'PICKED_UP', 'IN_TRANSIT', 'AT_DESTINATION']);
  const all = jobs.data?.data ?? [];
  const current = all.find((j) => ACTIVE.has(j.status));
  const needsResponse = all.filter((j) => needsOperatorAttention(j.status) && j.id !== current?.id);
  const availableCount = work.data?.data.length ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-h1 text-fg">{t('jobs:work.homeTitle')}</h1>
        <Button size="compact" onClick={() => navigate('/work')}>
          {t('jobs:work.findWork')}
        </Button>
      </div>

      <section aria-labelledby="current-job-heading">
        <h2 id="current-job-heading" className="text-label text-fg-secondary">
          {t('jobs:work.currentJob')}
        </h2>
        {current ? (
          <div className="mt-2">
            <JobCard
              reference={jobReference(current.id)}
              state={current.status}
              stateLabel={t(`jobs:status.${current.status}`)}
              route={{
                from: current.pickup_location?.address_text || '—',
                to: current.destination_location?.address_text || '—',
              }}
              cargo={current.cargo?.description ?? ''}
              price={current.agreed_price_kes != null ? formatKes(current.agreed_price_kes) : undefined}
              onClick={() => navigate(`/jobs/${current.id}`)}
            />
          </div>
        ) : (
          <div className="mt-2">
            <EmptyState title={t('jobs:work.noCurrentJob')} description={t('jobs:work.noCurrentJobBody')} />
          </div>
        )}
      </section>

      {needsResponse.length > 0 && (
        <section aria-labelledby="needs-response-heading">
          <h2 id="needs-response-heading" className="text-label text-fg-secondary" aria-live="polite">
            {t('jobs:work.needsResponse')} ({needsResponse.length})
          </h2>
          <ul className="mt-2 space-y-2">
            {needsResponse.map((job) => (
              <li key={job.id}>
                <AttentionRow job={job} />
              </li>
            ))}
          </ul>
        </section>
      )}

      <section aria-labelledby="available-work-heading">
        <h2 id="available-work-heading" className="text-label text-fg-secondary">
          {t('jobs:work.availableWork', { count: availableCount })}
        </h2>
        <div className="mt-2">
          <Link to="/work" className="text-body-sm font-medium text-action-secondary-text">
            {t('jobs:work.seeAll')}
          </Link>
        </div>
      </section>
    </div>
  );
}

function AttentionRow({ job }: { job: Job }): JSX.Element {
  const { t } = useTranslation('jobs');
  const action = operatorNextAction(job.status, false);
  return (
    <Link to={`/jobs/${job.id}`} className="block rounded-md">
      <Card interactive className="flex items-center justify-between gap-3">
        <div>
          <p className="font-semibold text-fg">{jobReference(job.id)}</p>
          <p className="text-body-sm text-fg-secondary">{job.destination_location?.address_text}</p>
        </div>
        {action && (
          <span className="text-body-sm font-medium text-action-secondary-text">
            {t(`jobs:workAction.${action}`)}
          </span>
        )}
      </Card>
    </Link>
  );
}
