import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ErrorState } from '@/components/ErrorState';
import { JobStatusHeader } from '@/components/JobStatusHeader';
import { JobTimeline, type TimelineStep } from '@/components/JobTimeline';
import { NextActionCard } from '@/components/NextActionCard';
import { PageLoader } from '@/components/PageLoader';
import { disputesApi } from '@/features/incidents/incidentsApi';
import { JobNotesSection } from '@/features/ops/JobNotesSection';
import { StaffJobPanel } from '@/features/ops/StaffJobPanel';
import { localizeError } from '@/services/errorMessage';

import { getOneShotGeo } from './geo';
import { jobsApi } from './jobsApi';
import {
  HAPPY_PATH_STATUSES,
  type OperatorActionKey,
  businessNextAction,
  happyPathIndex,
  operatorNextAction,
} from './jobHelpers';
import { formatKes } from './money';
import type { CancellationReason, Job, JobStatus } from './types';
import { useJobViewerRole } from './useJobViewerRole';

/** Formats an ISO timestamp as a local HH:MM — the same "as of HH:MM" /
 * timeline-time convention every wireframe screen uses. */
function hhmm(iso: string | null): string | undefined {
  if (!iso) return undefined;
  return new Date(iso).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
}

export function JobDetailPage(): JSX.Element {
  const { jobId } = useParams<{ jobId: string }>();
  const { t } = useTranslation(['jobs', 'incidents', 'errors']);
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

  function invalidateJob(): void {
    void qc.invalidateQueries({ queryKey: ['jobs', jobId] });
    void qc.invalidateQueries({ queryKey: ['jobs'] });
  }

  const arrivePickup = useMutation({
    mutationFn: async () => jobsApi.arrivePickup(jobId!, await getOneShotGeo(), crypto.randomUUID()),
    onSuccess: invalidateJob,
  });
  const startTransit = useMutation({
    mutationFn: () => jobsApi.startTransit(jobId!, crypto.randomUUID()),
    onSuccess: invalidateJob,
  });
  const arriveDestination = useMutation({
    mutationFn: async () => jobsApi.arriveDestination(jobId!, await getOneShotGeo(), crypto.randomUUID()),
    onSuccess: invalidateJob,
  });

  const viewer = useJobViewerRole(job.data?.business_id);

  if (job.isLoading || viewer.loading) return <PageLoader />;
  if (job.isError) {
    return <ErrorState message={localizeError(job.error, t)} onRetry={() => void job.refetch()} />;
  }
  const data = job.data!;

  const canCancel = data.next_allowed_statuses.includes('CANCELLED');
  const isOperatorViewer = viewer.role === 'OPERATOR';
  const isStaffViewer = viewer.role === 'STAFF';
  const operatorAction: OperatorActionKey | null = isOperatorViewer
    ? operatorNextAction(data.status, data.assigned_driver_id === viewer.operatorId)
    : null;
  const businessAction = viewer.role === 'BUSINESS' ? businessNextAction(data.status) : null;

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <JobStatusHeader
        state={data.status}
        stateLabel={t(`jobs:status.${data.status}`)}
        line={t(
          // NEGOTIATING's default line ("An operator has responded — review
          // their offer.") is written from the business's point of view —
          // wrong when the operator viewer is the one who just responded
          // and is waiting on the business. Every other status line reads
          // as a neutral progress description, correct for either role.
          isOperatorViewer && data.status === 'NEGOTIATING'
            ? 'jobs:statusLine.NEGOTIATING_OPERATOR'
            : `jobs:statusLine.${data.status}`,
        )}
      />

      {isStaffViewer ? (
        <StaffJobPanel job={data} isPlatformAdmin={viewer.isPlatformAdmin} />
      ) : isOperatorViewer ? (
        <OperatorNextActionSection
          action={operatorAction}
          onArrivePickup={() => arrivePickup.mutate()}
          arrivingPickup={arrivePickup.isPending}
          onStartTransit={() => startTransit.mutate()}
          startingTransit={startTransit.isPending}
          onArriveDestination={() => arriveDestination.mutate()}
          arrivingDestination={arriveDestination.isPending}
        />
      ) : (
        <NextActionSection
          action={businessAction}
          onRetrySubmit={() => retrySubmit.mutate()}
          retrying={retrySubmit.isPending}
        />
      )}

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

      <JobNotesSection jobId={data.id} />

      {/* A DRAFT job has no operator/driver relationship yet to report
          about; every later status is left to the server's own
          `party_kind_for_job` eligibility check rather than predicted here. */}
      {data.status !== 'DRAFT' && !isStaffViewer && (
        <div className="flex justify-end">
          <Link to={`/jobs/${jobId}/report-issue`} className="text-body-sm text-action-secondary-text underline">
            {t('incidents:report.entryLink')}
          </Link>
        </div>
      )}

      {/* Operator-side cancel (a different reason code, and — post-ASSIGNED
          — the late-cancellation consequence screen, §23) is out of scope
          this increment; only the Business's own cancel action renders. */}
      {canCancel && viewer.role === 'BUSINESS' && (
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
      {(arrivePickup.isError || startTransit.isError || arriveDestination.isError) && (
        <Alert tone="danger">
          {localizeError((arrivePickup.error ?? startTransit.error ?? arriveDestination.error)!, t)}
        </Alert>
      )}
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
  const disputes = useQuery({
    queryKey: ['disputes', jobId],
    queryFn: () => disputesApi.listForJob(jobId!),
    enabled: action === 'viewDispute' && !!jobId,
    retry: false,
  });

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
    const dispute = disputes.data?.data[0];
    if (dispute) {
      return (
        <NextActionCard
          action={{ label: t('jobs:action.viewDispute'), onClick: () => navigate(`/disputes/${dispute.id}`) }}
        />
      );
    }
    return <NextActionCard emptyLabel={t('jobs:action.viewDispute')} note={t('jobs:detail.comingSoon')} />;
  }
  // viewSummary — informational only, the read-only detail below already shows it.
  return <NextActionCard emptyLabel={t('jobs:detail.nothingNeeded')} />;
}

function OperatorNextActionSection({
  action,
  onArrivePickup,
  arrivingPickup,
  onStartTransit,
  startingTransit,
  onArriveDestination,
  arrivingDestination,
}: {
  action: OperatorActionKey | null;
  onArrivePickup: () => void;
  arrivingPickup: boolean;
  onStartTransit: () => void;
  startingTransit: boolean;
  onArriveDestination: () => void;
  arrivingDestination: boolean;
}): JSX.Element {
  const { t } = useTranslation('jobs');
  const navigate = useNavigate();
  const { jobId } = useParams<{ jobId: string }>();
  const disputes = useQuery({
    queryKey: ['disputes', jobId],
    queryFn: () => disputesApi.listForJob(jobId!),
    enabled: action === 'viewDispute' && !!jobId,
    retry: false,
  });

  if (!action) return <NextActionCard emptyLabel={t('jobs:detail.nothingNeeded')} />;

  if (action === 'respond') {
    return (
      <NextActionCard
        action={{ label: t('jobs:workAction.respond'), onClick: () => navigate(`/jobs/${jobId}/negotiation`) }}
      />
    );
  }
  if (action === 'assignDriverVehicle') {
    return (
      <NextActionCard
        action={{
          label: t('jobs:workAction.assignDriverVehicle'),
          onClick: () => navigate(`/jobs/${jobId}/assign`),
        }}
      />
    );
  }
  // ASSIGNED — no geofence gate exists (chain-of-custody.md §5), so "Go to
  // pickup" (external map/call) and "I'm at pickup" (the [server] action)
  // render together on this one screen rather than as separate steps.
  if (action === 'arriveAtPickup') {
    return (
      <NextActionCard
        driver
        action={{ label: t('jobs:workAction.arriveAtPickup'), onClick: onArrivePickup, loading: arrivingPickup }}
        note={t('jobs:workAction.arriveAtPickupNote')}
      />
    );
  }
  if (action === 'confirmPickup') {
    return (
      <NextActionCard
        driver
        action={{ label: t('jobs:workAction.confirmPickup'), onClick: () => navigate(`/jobs/${jobId}/pickup-proof`) }}
      />
    );
  }
  if (action === 'startTransit') {
    return (
      <NextActionCard
        driver
        action={{ label: t('jobs:workAction.startTransit'), onClick: onStartTransit, loading: startingTransit }}
      />
    );
  }
  if (action === 'arriveAtDestination') {
    return (
      <NextActionCard
        driver
        action={{
          label: t('jobs:workAction.arriveAtDestination'),
          onClick: onArriveDestination,
          loading: arrivingDestination,
        }}
      />
    );
  }
  if (action === 'confirmDelivery') {
    return (
      <NextActionCard
        driver
        action={{
          label: t('jobs:workAction.confirmDelivery'),
          onClick: () => navigate(`/jobs/${jobId}/delivery-proof`),
        }}
      />
    );
  }
  if (action === 'viewStatement') {
    // No operator-facing commission-preview endpoint exists yet — deferred.
    return <NextActionCard emptyLabel={t('jobs:detail.autoCompleteNote')} note={t('jobs:detail.comingSoon')} />;
  }
  if (action === 'viewDispute') {
    const dispute = disputes.data?.data[0];
    if (dispute) {
      return (
        <NextActionCard
          action={{ label: t('jobs:workAction.viewDispute'), onClick: () => navigate(`/disputes/${dispute.id}`) }}
        />
      );
    }
    return <NextActionCard emptyLabel={t('jobs:workAction.viewDispute')} note={t('jobs:detail.comingSoon')} />;
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
