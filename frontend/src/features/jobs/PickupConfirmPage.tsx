import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ErrorState } from '@/components/ErrorState';
import { PageLoader } from '@/components/PageLoader';
import { localizeError } from '@/services/errorMessage';

import { jobsApi } from './jobsApi';

/**
 * Business pickup confirmation (`design-phase-3-wireframes.md` §6.6) — the
 * business-side rendering of one of the two always-valid pickup proofs.
 *
 * Known gap: §6.6's "Who" section (driver name + vehicle class + plate)
 * needs data the Job DTO doesn't carry (`job_detail()` exposes only
 * `assigned_driver_id`/`assigned_vehicle_id`, not names), and there is no
 * endpoint a business can call to read an arbitrary operator's/vehicle's
 * detail — `vehicles`/`operators` read policies scope to the resource's own
 * owner, not an unrelated business party to the job. Omitted here rather
 * than faked; flagged in the Increment 2 report for a founder decision on
 * whether a future increment should add a business-facing read surface for
 * this (e.g. a small assignment-summary field on the Job DTO).
 */
export function PickupConfirmPage(): JSX.Element {
  const { jobId } = useParams<{ jobId: string }>();
  const { t } = useTranslation(['jobs', 'errors']);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [acknowledged, setAcknowledged] = useState(false);
  const [confirming, setConfirming] = useState(false);

  const job = useQuery({
    queryKey: ['jobs', jobId],
    queryFn: () => jobsApi.get(jobId!),
    enabled: !!jobId,
    retry: false,
  });

  const confirm = useMutation({
    mutationFn: () => jobsApi.confirmPickupBusiness(jobId!, {}, crypto.randomUUID()),
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

  if (data.status !== 'AT_PICKUP') {
    return (
      <Card>
        <Alert tone="info">{t('jobs:pickupConfirm.movedOn')}</Alert>
        <div className="mt-3">
          <Button variant="secondary" onClick={() => navigate(`/jobs/${jobId}`, { replace: true })}>
            {t('jobs:pickupConfirm.backToJob')}
          </Button>
        </div>
      </Card>
    );
  }

  return (
    <div className="mx-auto max-w-lg space-y-4">
      <Card>
        <p className="text-body text-fg">
          {t('jobs:pickupConfirm.whatYoureConfirming', {
            cargo: data.cargo?.description ?? '',
            ref: data.id.slice(-6).toUpperCase(),
            location: data.pickup_location?.address_text ?? '',
          })}
        </p>
        <p className="mt-3 text-body-sm text-fg-secondary">{t('jobs:pickupConfirm.consequence')}</p>

        <label className="mt-4 flex items-start gap-2 text-body-sm text-fg">
          <input
            type="checkbox"
            className="mt-0.5 h-4 w-4 rounded border-line-strong"
            checked={acknowledged}
            onChange={(e) => setAcknowledged(e.target.checked)}
          />
          {t('jobs:pickupConfirm.acknowledge')}
        </label>

        {!confirming ? (
          <div className="mt-4">
            <Button fullWidth disabled={!acknowledged} onClick={() => setConfirming(true)}>
              {t('jobs:pickupConfirm.confirmPickup')}
            </Button>
          </div>
        ) : (
          <div className="mt-4 space-y-2 rounded-md border border-line-strong bg-surface-sunken p-3">
            <p className="text-body-sm text-fg">
              {t('jobs:pickupConfirm.confirmStep', { ref: data.id.slice(-6).toUpperCase() })}
            </p>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                size="compact"
                onClick={() => setConfirming(false)}
                disabled={confirm.isPending}
              >
                {t('jobs:create.back')}
              </Button>
              <Button size="compact" loading={confirm.isPending} onClick={() => confirm.mutate()}>
                {t('jobs:pickupConfirm.yesConfirm')}
              </Button>
            </div>
          </div>
        )}

        {confirm.isError && (
          <div className="mt-3">
            <Alert tone="danger">{localizeError(confirm.error, t)}</Alert>
          </div>
        )}
      </Card>
    </div>
  );
}
