import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { useLocation, useNavigate, useParams } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ErrorState } from '@/components/ErrorState';
import { Icon } from '@/design/Icon';
import { PageLoader } from '@/components/PageLoader';
import { localizeError } from '@/services/errorMessage';

import { jobReference } from './jobHelpers';
import { jobsApi } from './jobsApi';

/**
 * Custody confirmation (`design-phase-3-wireframes.md` §12.1) — the
 * one-time screen reached right after a successful pickup-proof submit.
 * Returning to Current Job home while still `PICKED_UP` shows "Start
 * transit" there directly (not gated behind revisiting this screen).
 */
export function CustodyConfirmationPage(): JSX.Element {
  const { jobId } = useParams<{ jobId: string }>();
  const { t } = useTranslation(['jobs', 'errors']);
  const navigate = useNavigate();
  const location = useLocation();
  const qc = useQueryClient();
  // Passed forward from PickupProofPage — the Job DTO itself carries no
  // proof-method field (a documented gap). A direct reload of this screen
  // loses the state and falls back to "verified", the more common path.
  const attested = (location.state as { attested?: boolean } | null)?.attested ?? false;

  const job = useQuery({
    queryKey: ['jobs', jobId],
    queryFn: () => jobsApi.get(jobId!),
    enabled: !!jobId,
    retry: false,
  });

  const startTransit = useMutation({
    mutationFn: () => jobsApi.startTransit(jobId!, crypto.randomUUID()),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['jobs', jobId] });
      void qc.invalidateQueries({ queryKey: ['jobs'] });
      navigate(`/jobs/${jobId}`, { replace: true });
    },
  });

  if (job.isLoading) return <PageLoader />;
  if (job.isError) {
    return <ErrorState message={localizeError(job.error, t)} onRetry={() => void job.refetch()} />;
  }
  const data = job.data!;

  return (
    <div className="mx-auto max-w-lg space-y-4">
      <Card>
        <div className="flex items-center gap-2 text-status-success-fg">
          <Icon name="check" size={24} />
          <h1 className="text-h2 text-fg">{t('jobs:custody.goodsReceived')}</h1>
        </div>
        <p className="mt-2 text-body-sm text-fg-secondary">
          {t('jobs:custody.ref', { ref: jobReference(data.id) })}
        </p>
        <p className="mt-3 flex items-center gap-1.5 text-body text-fg-secondary">
          <Icon name={attested ? 'alertTriangle' : 'check'} size={16} />
          {t(attested ? 'jobs:custody.attestedUnverified' : 'jobs:custody.verified')}
        </p>
      </Card>

      <Button
        size="driver"
        fullWidth
        loading={startTransit.isPending}
        onClick={() => startTransit.mutate()}
      >
        {t('jobs:workAction.startTransit')}
      </Button>
      <Button variant="secondary" fullWidth onClick={() => navigate(`/jobs/${jobId}`, { replace: true })}>
        {t('jobs:custody.doneForNow')}
      </Button>

      {startTransit.isError && <Alert tone="danger">{localizeError(startTransit.error, t)}</Alert>}
    </div>
  );
}
