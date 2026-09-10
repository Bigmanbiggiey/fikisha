import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ErrorState } from '@/components/ErrorState';
import { PageLoader } from '@/components/PageLoader';
import { StatusBadge } from '@/components/StatusBadge';
import { vehicleStatusBadge } from '@/components/vehicleStatus';
import { VerificationPanel } from '@/features/verification/VerificationPanel';
import { localizeError } from '@/services/errorMessage';

import { OPERATOR_STATUSES, vehiclesApi } from './vehiclesApi';

export function VehicleDetailPage(): JSX.Element {
  const { vehicleId = '' } = useParams();
  const { t } = useTranslation(['org', 'errors']);
  const qc = useQueryClient();

  const vehicle = useQuery({
    queryKey: ['vehicle', vehicleId],
    queryFn: () => vehiclesApi.get(vehicleId),
    retry: false,
  });

  const setStatus = useMutation({
    mutationFn: (status: string) => vehiclesApi.setStatus(vehicleId, status),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['vehicle', vehicleId] }),
  });

  if (vehicle.isLoading) return <PageLoader />;
  if (vehicle.isError || !vehicle.data) {
    return (
      <ErrorState message={localizeError(vehicle.error, t)} onRetry={() => void vehicle.refetch()} />
    );
  }
  const v = vehicle.data;

  return (
    <div className="space-y-5">
      <Link to="/vehicles" className="text-body-sm text-action-secondary-text">
        &larr; {t('org:common.back')}
      </Link>

      <Card>
        <div className="flex items-center justify-between gap-3">
          <h1 className="text-h1 text-fg">{v.registration}</h1>
          <span className="flex flex-wrap gap-2">
            {v.vehicle_class_heavy && (
              <StatusBadge tone="brand" label={t('org:vehicles.heavy')} />
            )}
            <StatusBadge {...vehicleStatusBadge(v.status)} />
          </span>
        </div>
        <dl className="mt-3 space-y-1 text-body-sm">
          <Row label={t('org:vehicles.class')} value={v.vehicle_class} />
          <Row label={t('org:vehicles.capacity')} value={`${v.capacity_value} ${v.capacity_unit}`} />
          <Row label={t('org:vehicles.controller')} value={v.controller_kind} />
          <Row label={t('org:vehicles.make')} value={v.make || '—'} />
        </dl>

        {v.status === 'SUSPENDED' ? (
          <div className="mt-4">
            <Alert tone="warning">
              This vehicle is suspended by an administrator. / Gari hili limezimwa na msimamizi.
            </Alert>
          </div>
        ) : (
          <div className="mt-4 flex flex-wrap gap-2 border-t border-line pt-4">
            {OPERATOR_STATUSES.map((s) => (
              <Button
                key={s}
                variant={v.status === s ? 'primary' : 'secondary'}
                onClick={() => setStatus.mutate(s)}
                disabled={setStatus.isPending || v.status === s}
              >
                {s}
              </Button>
            ))}
          </div>
        )}
      </Card>

      <VerificationPanel subjectType="VEHICLE" subjectId={v.id} />
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }): JSX.Element {
  return (
    <div className="flex justify-between">
      <dt className="text-fg-muted">{label}</dt>
      <dd className="font-medium text-fg">{value}</dd>
    </div>
  );
}
