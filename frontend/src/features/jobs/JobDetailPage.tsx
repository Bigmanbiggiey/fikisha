import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ErrorState } from '@/components/ErrorState';
import { JobStatusHeader } from '@/components/JobStatusHeader';
import { JobTimeline, type TimelineStep } from '@/components/JobTimeline';
import { NextActionCard } from '@/components/NextActionCard';
import { PageLoader } from '@/components/PageLoader';
import { localizeError } from '@/services/errorMessage';

import { jobsApi } from './jobsApi';
import { HAPPY_PATH_STATUSES, businessNextAction, happyPathIndex } from './jobHelpers';
import { formatKes } from './money';
import type { CancellationReason, Job, JobStatus } from './types';

/** Formats an ISO timestamp as a local HH:MM — the same "as of HH:MM" /
 * timeline-time convention every wireframe screen uses. */
function hhmm(iso: string | null): string | undefined {
  if (!iso) return undefined;
  return new Date(iso).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
}

export function JobDetailPage(): JSX.Element {
  const { jobId } = useParams<{ jobId: string }>();
  const { t } = useTranslation(['jobs', 'errors']);
  const qc = useQueryClient();

  const job = useQuery({
    queryKey: ['jobs', jobId],
    queryFn: () => jobsApi.get(jobId!),
    enabled: !!jobId,
    retry: false,
  });

  const cancel = useMutation({
    mutationFn: (reasonCode: CancellationReason) =>
      jobsApi.cancel(jobId!, { reason_code: reasonCode }, crypto.randomUUID()),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['jobs', jobId] });
      void qc.invalidateQueries({ queryKey: ['jobs'] });
    },
  });

  const retrySubmit = useMutation({
    mutationFn: () => jobsApi.submit(jobId!, crypto.randomUUID()),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['jobs', jobId] }),
  });

  if (job.isLoading) return <PageLoader />;
  if (job.isError) {
    return <ErrorState message={localizeError(job.error, t)} onRetry={() => void job.refetch()} />;
  }
  const data = job.data!;

  const canCancel = data.next_allowed_statuses.includes('CANCELLED');
  const action = businessNextAction(data.status);

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <JobStatusHeader
        state={data.status}
        stateLabel={t(`jobs:status.${data.status}`)}
        line={t(`jobs:statusLine.${data.status}`)}
      />

      <NextActionSection action={action} onRetrySubmit={() => retrySubmit.mutate()} retrying={retrySubmit.isPending} />

      <Card>
        <h2 className="text-label text-fg-secondary">{t('jobs:detail.route')}</h2>
        <dl className="mt-2 space-y-1 text-body">
          <div className="flex justify-between gap-3">
            <dt className="text-fg-muted">{t('jobs:detail.pickup')}</dt>
            <dd className="text-fg">{data.pickup_location?.address_text || '—'}</dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-fg-muted">{t('jobs:detail.destination')}</dt>
            <dd className="text-fg">
              {data.destination_location?.address_text || '—'}
              {data.recipient_name && ` — ${data.recipient_name}`}
            </dd>
          </div>
        </dl>
      </Card>

      <Card>
        <h2 className="text-label text-fg-secondary">{t('jobs:detail.cargo')}</h2>
        <p className="mt-2 text-body text-fg">{data.cargo?.description || '—'}</p>
        {data.cargo?.handling_flags && data.cargo.handling_flags.length > 0 && (
          <p className="mt-1 text-body-sm text-fg-secondary">{data.cargo.handling_flags.join(' · ')}</p>
        )}
      </Card>

      <Card>
        <h2 className="text-label text-fg-secondary">{t('jobs:detail.price')}</h2>
        <p className="mt-2 fk-numeric text-h3 text-fg">
          {data.agreed_price_kes != null
            ? `${formatKes(data.agreed_price_kes)} (${t('jobs:detail.agreed')})`
            : data.proposed_price_kes != null
              ? `${formatKes(data.proposed_price_kes)} (${t('jobs:detail.proposed')})`
              : '—'}
        </p>
      </Card>

      <Card>
        <h2 className="text-label text-fg-secondary">{t('jobs:detail.timeline')}</h2>
        <div className="mt-3">
          <Timeline job={data} />
        </div>
      </Card>

      {canCancel && (
        <div className="flex justify-end">
          <Button
            variant="destructive"
            size="compact"
            loading={cancel.isPending}
            onClick={() => cancel.mutate('BUSINESS_CHANGED_MIND')}
          >
            {t('jobs:detail.cancel')}
          </Button>
        </div>
      )}
      {cancel.isError && <Alert tone="danger">{localizeError(cancel.error, t)}</Alert>}
    </div>
  );
}

function NextActionSection({
  action,
  onRetrySubmit,
  retrying,
}: {
  action: ReturnType<typeof businessNextAction>;
  onRetrySubmit: () => void;
  retrying: boolean;
}): JSX.Element {
  const { t } = useTranslation('jobs');
  const navigate = useNavigate();
  const { jobId } = useParams<{ jobId: string }>();

  if (!action) return <NextActionCard emptyLabel={t('jobs:detail.nothingNeeded')} />;

  if (action === 'continueRequest') {
    return (
      <NextActionCard
        action={{ label: t('jobs:action.continueRequest'), onClick: onRetrySubmit, loading: retrying }}
        note={t('jobs:detail.draftNote')}
      />
    );
  }
  if (action === 'confirmPickup') {
    return (
      <NextActionCard action={{ label: t('jobs:action.confirmPickup'), onClick: () => navigate(`/jobs/${jobId}/confirm-pickup`) }} />
    );
  }
  if (action === 'confirmCompletion') {
    // No manual "confirm completion" endpoint exists — DELIVERED -> COMPLETED
    // only happens automatically (see jobHelpers.ts businessNextAction doc).
    return <NextActionCard emptyLabel={t('jobs:detail.autoCompleteNote')} />;
  }
  if (action === 'reviewOffers') {
    return (
      <NextActionCard
        action={{ label: t('jobs:action.reviewOffers'), onClick: () => navigate(`/jobs/${jobId}/negotiation`) }}
      />
    );
  }
  if (action === 'viewDispute') {
    return <NextActionCard emptyLabel={t(`jobs:action.${action}`)} note={t('jobs:detail.comingSoon')} />;
  }
  // viewSummary — informational only, the read-only detail below already shows it.
  return <NextActionCard emptyLabel={t('jobs:detail.nothingNeeded')} />;
}

function Timeline({ job }: { job: Job }): JSX.Element {
  const { t } = useTranslation('jobs');
  const isTerminalNegative = job.status === 'CANCELLED' || job.status === 'FAILED';
  const isDisputed = job.status === 'DISPUTED';
  const isFrozen = isTerminalNegative || isDisputed;

  const timestampByStatus: Partial<Record<JobStatus, string | null>> = {
    REQUESTED: job.timestamps.published_at,
    CONFIRMED: job.timestamps.confirmed_at,
    ASSIGNED: job.timestamps.assigned_at,
    PICKED_UP: job.timestamps.picked_up_at,
    DELIVERED: job.timestamps.delivered_at,
    COMPLETED: job.timestamps.completed_at,
  };

  // CANCELLED/FAILED/DISPUTED aren't HAPPY_PATH_STATUSES members, so
  // happyPathIndex(job.status) would return -1 for a frozen job and hide
  // every prior step's checkmark. Derive "how far did it get" from the
  // last populated timestamp instead — a later step's timestamp only ever
  // appears once every preceding happy-path step has actually happened.
  const lastReachedIndex = HAPPY_PATH_STATUSES.reduce(
    (acc, status, i) => (timestampByStatus[status] ? i : acc),
    -1,
  );
  const currentIndex = isFrozen ? lastReachedIndex : happyPathIndex(job.status);

  const steps: TimelineStep[] = HAPPY_PATH_STATUSES.map((status, i) => ({
    id: status,
    label: t(`jobs:status.${status}`),
    node: isFrozen ? (i <= currentIndex ? 'done' : 'upcoming') : i < currentIndex ? 'done' : i === currentIndex ? 'current' : 'upcoming',
    time: hhmm(timestampByStatus[status] ?? null),
  }));

  return (
    <JobTimeline
      steps={steps}
      endCap={isTerminalNegative ? (job.status === 'CANCELLED' ? 'cancelled' : 'failed') : isDisputed ? 'disputed' : undefined}
      endCapText={isFrozen ? t(`jobs:status.${job.status}`) : undefined}
    />
  );
}
