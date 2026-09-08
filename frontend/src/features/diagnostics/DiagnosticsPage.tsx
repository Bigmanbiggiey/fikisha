import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';

import { Card } from '@/components/Card';
import { ErrorState } from '@/components/ErrorState';
import { PageLoader } from '@/components/PageLoader';
import { StatusBadge } from '@/components/StatusBadge';
import { localizeError } from '@/services/errorMessage';

import { diagnosticsApi } from './diagnosticsApi';

export function DiagnosticsPage(): JSX.Element {
  const { t } = useTranslation(['common', 'errors']);

  const health = useQuery({
    queryKey: ['health'],
    queryFn: () => diagnosticsApi.health(),
    retry: false,
  });

  const reference = useQuery({
    queryKey: ['reference'],
    queryFn: () => diagnosticsApi.reference(),
    retry: false,
  });

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold text-slate-900">{t('common:diagnostics.title')}</h1>

      <Card>
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-slate-700">{t('common:diagnostics.apiHealth')}</span>
          {health.isLoading ? (
            <PageLoader />
          ) : health.isError || health.data?.status !== 'ok' ? (
            <StatusBadge tone="negative" label={t('common:diagnostics.unreachable')} />
          ) : (
            <StatusBadge tone="positive" label={t('common:diagnostics.healthy')} />
          )}
        </div>
      </Card>

      <Card>
        <span className="text-sm font-medium text-slate-700">{t('common:diagnostics.reference')}</span>
        {reference.isLoading ? (
          <PageLoader />
        ) : reference.isError ? (
          <div className="mt-3">
            <ErrorState
              message={localizeError(reference.error, t)}
              onRetry={() => void reference.refetch()}
            />
          </div>
        ) : reference.data ? (
          <dl className="mt-3 space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-slate-500">{t('common:diagnostics.configVersion')}</dt>
              <dd className="font-medium text-slate-800">{reference.data.config_version}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">{t('common:diagnostics.supportedLocales')}</dt>
              <dd className="font-medium text-slate-800">
                {reference.data.locales.supported.join(', ')}
              </dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500">{t('common:diagnostics.vehicleTypes')}</dt>
              <dd className="text-right font-medium text-slate-800">
                {reference.data.vehicle_types.join(', ')}
              </dd>
            </div>
          </dl>
        ) : null}
      </Card>
    </div>
  );
}
