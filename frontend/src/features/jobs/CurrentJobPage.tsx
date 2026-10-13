import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Link, Navigate, useNavigate } from 'react-router-dom';

import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { JobCard } from '@/components/JobCard';
import { PageLoader } from '@/components/PageLoader';
import { localizeError } from '@/services/errorMessage';
import { useActiveRole } from '@/shell/activeRole';
import { useWorkspaces } from '@/shell/useWorkspaces';

import { jobReference } from './jobHelpers';
import { jobsApi } from './jobsApi';
import type { JobStatus } from './types';

/** A driver's assignment is "current" until the goods are delivered. A
 * DISPUTED job stays here so the driver sees it is on hold. */
const CURRENT: readonly JobStatus[] = ['ASSIGNED', 'AT_PICKUP', 'PICKED_UP', 'IN_TRANSIT', 'AT_DESTINATION', 'DISPUTED'];

/**
 * The driver's "Current job" tab (Design Phase 7 P-04; P1 §7, P3 §10.1).
 * - one current assignment: opens that job, which renders the driver's
 *   Current job view (10b);
 * - several: a short list to pick from;
 * - none: "No active job". Available work is offered only where the driver
 *   may take work (P1 §7 clarification): an individual operator, or a group
 *   driver whose group is in DRIVER_ACCEPTS mode. Otherwise: "you'll be
 *   notified when you're assigned".
 */
export function CurrentJobPage(): JSX.Element {
  const { t } = useTranslation(['jobs', 'errors']);
  const navigate = useNavigate();
  const { loading, workspaces } = useWorkspaces();
  const { roles } = useActiveRole();
  const jobs = useQuery({ queryKey: ['jobs'], queryFn: jobsApi.list, retry: false });

  if (loading || jobs.isLoading) return <PageLoader />;
  if (jobs.isError) {
    return <ErrorState message={localizeError(jobs.error, t)} onRetry={() => void jobs.refetch()} />;
  }

  const operatorId = workspaces.find((w) => w.kind === 'OPERATOR')?.id ?? null;
  const current = (jobs.data?.data ?? []).filter(
    (job) => !!operatorId && job.assigned_driver_id === operatorId && CURRENT.includes(job.status),
  );

  if (current.length === 1) return <Navigate to={`/jobs/${current[0]!.id}`} replace />;

  if (current.length === 0) {
    const mayTakeWork =
      roles.includes('OPERATOR') ||
      workspaces.some((w) => w.kind === 'DRIVER' && w.assignmentMode === 'DRIVER_ACCEPTS');
    return (
      <div className="space-y-4">
        <h1 className="text-h1 text-fg">{t('jobs:currentJob.title')}</h1>
        <EmptyState
          title={t('jobs:currentJob.none')}
          description={mayTakeWork ? undefined : t('jobs:currentJob.noneNotified')}
          action={
            mayTakeWork ? (
              <Link to="/work" className="text-body text-action-secondary-text underline">
                {t('jobs:currentJob.availableWork')}
              </Link>
            ) : undefined
          }
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h1 className="text-h1 text-fg">{t('jobs:currentJob.title')}</h1>
      <p className="text-body text-fg-secondary">{t('jobs:currentJob.several', { count: current.length })}</p>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {current.map((job) => (
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
            onClick={() => navigate(`/jobs/${job.id}`)}
          />
        ))}
      </div>
    </div>
  );
}
