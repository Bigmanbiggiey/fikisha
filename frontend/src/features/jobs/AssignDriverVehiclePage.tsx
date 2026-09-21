import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { EligibilityRow } from '@/components/EligibilityRow';
import { ErrorState } from '@/components/ErrorState';
import { PageLoader } from '@/components/PageLoader';
import { localizeError } from '@/services/errorMessage';

import { jobReference } from './jobHelpers';
import { jobsApi } from './jobsApi';

/**
 * Assign driver & vehicle (`design-phase-3-wireframes.md` §9.1/§9.2) —
 * individual-operator-only this increment (the driver pool is always just
 * the confirmed operator themself; a Group Manager's driver-pool flow is
 * deferred). The candidate list previews server-computed eligibility, but
 * the UI never trusts its own cached copy at submit time — `assign()` is
 * the authoritative call, and a server rejection (driver/vehicle went
 * ineligible between selection and confirm) shows the specific reason and
 * refetches candidates rather than silently forcing the assignment through.
 */
export function AssignDriverVehiclePage(): JSX.Element {
  const { jobId } = useParams<{ jobId: string }>();
  const { t } = useTranslation(['jobs', 'errors']);
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [driverId, setDriverId] = useState<string | null>(null);
  const [vehicleId, setVehicleId] = useState<string | null>(null);

  const job = useQuery({
    queryKey: ['jobs', jobId],
    queryFn: () => jobsApi.get(jobId!),
    enabled: !!jobId,
    retry: false,
  });

  const candidates = useQuery({
    queryKey: ['jobs', jobId, 'assignment-candidates'],
    queryFn: () => jobsApi.assignmentCandidates(jobId!),
    enabled: !!jobId,
    retry: false,
  });

  // Individual-operator case: there is exactly one driver candidate — no
  // real choice, so default it selected once it loads.
  useEffect(() => {
    const drivers = candidates.data?.drivers ?? [];
    const onlyDriver = drivers.length === 1 ? drivers[0] : undefined;
    if (driverId === null && onlyDriver?.eligible) {
      setDriverId(onlyDriver.id);
    }
  }, [candidates.data, driverId]);

  const assign = useMutation({
    mutationFn: () =>
      jobsApi.assign(
        jobId!,
        { driver_profile_id: driverId!, vehicle_id: vehicleId! },
        crypto.randomUUID(),
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['jobs', jobId] });
      void qc.invalidateQueries({ queryKey: ['jobs'] });
      navigate(`/jobs/${jobId}`, { replace: true });
    },
    onError: () => {
      // The candidate preview may now be stale (§9.2's documented exception)
      // — refetch so the reason and any newly-ineligible row are current.
      void qc.invalidateQueries({ queryKey: ['jobs', jobId, 'assignment-candidates'] });
    },
  });

  if (job.isLoading || candidates.isLoading) return <PageLoader />;
  if (job.isError) {
    return <ErrorState message={localizeError(job.error, t)} onRetry={() => void job.refetch()} />;
  }
  if (candidates.isError) {
    return (
      <ErrorState message={localizeError(candidates.error, t)} onRetry={() => void candidates.refetch()} />
    );
  }
  const data = job.data!;
  const c = candidates.data!;

  if (data.status !== 'CONFIRMED') {
    return (
      <Card>
        <Alert tone="info">{t('jobs:assign.movedOn')}</Alert>
        <div className="mt-3">
          <Button variant="secondary" onClick={() => navigate(`/jobs/${jobId}`, { replace: true })}>
            {t('jobs:pickupConfirm.backToJob')}
          </Button>
        </div>
      </Card>
    );
  }

  if (!c.supports_group_assignment && c.drivers.length === 0) {
    // A group-confirmed job — the Group Manager driver-pool flow isn't built
    // yet this increment (founder scope decision, 2026-09-21).
    return (
      <Card>
        <Alert tone="info">{t('jobs:assign.groupNotSupported')}</Alert>
      </Card>
    );
  }

  const canSubmit = !!driverId && !!vehicleId && !c.blocked;

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <div>
        <h1 className="text-h1 text-fg">{t('jobs:assign.title')}</h1>
        <p className="text-body-sm text-fg-secondary">
          {t('jobs:assign.forJob', { ref: jobReference(data.id) })}
        </p>
      </div>

      {c.blocked && <Alert tone="warning">{c.blocked}</Alert>}

      <Card>
        <h2 className="text-label text-fg-secondary">{t('jobs:assign.chooseDriver')}</h2>
        <div role="radiogroup" aria-label={t('jobs:assign.chooseDriver')} className="mt-2 space-y-2">
          {c.drivers.map((d) => (
            <EligibilityRow
              key={d.id}
              name="driver"
              value={d.id}
              label={d.name}
              meta={t('jobs:assign.trustLevel', { level: d.trust_level || t('jobs:assign.noLevel') })}
              eligible={d.eligible}
              reasons={d.reasons}
              selected={driverId === d.id}
              onSelect={setDriverId}
            />
          ))}
        </div>
      </Card>

      <Card>
        <h2 className="text-label text-fg-secondary">{t('jobs:assign.chooseVehicle')}</h2>
        {c.vehicles.length === 0 ? (
          <p className="mt-2 text-body-sm text-fg-secondary">{t('jobs:assign.noVehicles')}</p>
        ) : (
          <div role="radiogroup" aria-label={t('jobs:assign.chooseVehicle')} className="mt-2 space-y-2">
            {c.vehicles.map((v) => (
              <EligibilityRow
                key={v.id}
                name="vehicle"
                value={v.id}
                label={`${v.registration} — ${v.vehicle_class ?? ''}`}
                meta={t('jobs:assign.capacity', { value: v.capacity_value, unit: v.capacity_unit })}
                eligible={v.eligible}
                reasons={v.reasons}
                selected={vehicleId === v.id}
                onSelect={setVehicleId}
              />
            ))}
          </div>
        )}
      </Card>

      {assign.isError && <Alert tone="danger">{localizeError(assign.error, t)}</Alert>}

      <Button fullWidth disabled={!canSubmit} loading={assign.isPending} onClick={() => assign.mutate()}>
        {t('jobs:assign.confirm')}
      </Button>
    </div>
  );
}
