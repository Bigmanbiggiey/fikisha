import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { Field } from '@/components/Field';
import { Input } from '@/components/Input';
import { PageLoader } from '@/components/PageLoader';
import { StatusBadge } from '@/components/StatusBadge';
import { localizeError } from '@/services/errorMessage';

import { orgApi } from './orgApi';
import { BASE_TYPES } from './types';

export function OperatingLocationsPage(): JSX.Element {
  const { t } = useTranslation(['org', 'errors']);
  const qc = useQueryClient();

  const list = useQuery({
    queryKey: ['operating-locations'],
    queryFn: orgApi.listOperatingLocations,
    retry: false,
  });

  const [name, setName] = useState('');
  const [type, setType] = useState<string>('STAGE');
  const [landmark, setLandmark] = useState('');
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () =>
      orgApi.createOperatingLocation({
        name: name.trim(),
        type,
        landmark: landmark.trim(),
        zone_code: 'KITENGELA',
      }),
    onSuccess: () => {
      setName('');
      setLandmark('');
      setError(null);
      void qc.invalidateQueries({ queryKey: ['operating-locations'] });
    },
    onError: (err) => setError(localizeError(err, t)),
  });

  return (
    <div className="space-y-5">
      <h1 className="text-h1 text-fg">{t('org:locations.title')}</h1>

      <Card>
        <h2 className="text-label text-fg-secondary">{t('org:locations.createTitle')}</h2>
        <form
          className="mt-3 space-y-3"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            if (name.trim()) create.mutate();
          }}
        >
          <Field label={t('org:locations.name')}>
            {({ id }) => (
              <Input id={id} value={name} onChange={(e) => setName(e.target.value)} required />
            )}
          </Field>
          <div className="flex gap-3">
            <label className="text-sm">
              <span className="mb-1 block font-medium text-fg-secondary">{t('org:locations.type')}</span>
              <select
                className="min-h-target rounded-md border border-line-strong bg-surface-input px-2 text-body-sm text-fg"
                value={type}
                onChange={(e) => setType(e.target.value)}
              >
                {BASE_TYPES.map((ty) => (
                  <option key={ty} value={ty}>
                    {ty}
                  </option>
                ))}
              </select>
            </label>
            <div className="flex-1">
              <Field label={t('org:locations.landmark')}>
                {({ id }) => (
                  <Input id={id} value={landmark} onChange={(e) => setLandmark(e.target.value)} />
                )}
              </Field>
            </div>
          </div>
          <Button type="submit" loading={create.isPending} disabled={!name.trim()}>
            {t('org:common.create')}
          </Button>
          {error && <Alert tone="danger">{error}</Alert>}
        </form>
      </Card>

      {list.isLoading ? (
        <PageLoader />
      ) : list.isError ? (
        <ErrorState message={localizeError(list.error, t)} onRetry={() => void list.refetch()} />
      ) : list.data && list.data.data.length > 0 ? (
        <ul className="space-y-2">
          {list.data.data.map((b) => (
            <li key={b.id}>
              <Card>
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-fg">{b.name}</span>
                  <StatusBadge label={b.type} />
                </div>
                {b.landmark && <p className="mt-1 text-body-sm text-fg-muted">{b.landmark}</p>}
              </Card>
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState title={t('org:locations.empty')} />
      )}
    </div>
  );
}
