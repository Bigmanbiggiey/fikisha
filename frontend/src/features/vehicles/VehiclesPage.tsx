import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { Field } from '@/components/Field';
import { Input } from '@/components/Input';
import { PageLoader } from '@/components/PageLoader';
import { StatusBadge } from '@/components/StatusBadge';
import { vehicleStatusBadge } from '@/components/vehicleStatus';
import { orgApi } from '@/features/org/orgApi';
import { localizeError } from '@/services/errorMessage';

import { CAPACITY_UNITS, VEHICLE_CLASSES, vehiclesApi } from './vehiclesApi';

export function VehiclesPage(): JSX.Element {
  const { t } = useTranslation(['org', 'errors']);
  const qc = useQueryClient();

  const list = useQuery({ queryKey: ['vehicles'], queryFn: vehiclesApi.list, retry: false });
  const me = useQuery({ queryKey: ['operator', 'me'], queryFn: orgApi.getMyOperator, retry: false });
  const groups = useQuery({ queryKey: ['groups'], queryFn: orgApi.listGroups, retry: false });

  const [vehicleClass, setVehicleClass] = useState<string>('PICKUP');
  const [registration, setRegistration] = useState('');
  const [capacity, setCapacity] = useState('');
  const [unit, setUnit] = useState<string>('KG');
  const [groupId, setGroupId] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  const manageableGroups = (groups.data?.data ?? []).filter(
    (g) => g.my_role === 'OWNER' || g.my_role === 'MANAGER',
  );

  const create = useMutation({
    mutationFn: () =>
      vehiclesApi.create({
        vehicle_class: vehicleClass,
        registration: registration.trim(),
        capacity_value: capacity,
        capacity_unit: unit,
        ...(groupId
          ? { owner_group_id: groupId }
          : { owner_operator_id: me.data?.id }),
      }),
    onSuccess: () => {
      setRegistration('');
      setCapacity('');
      setError(null);
      void qc.invalidateQueries({ queryKey: ['vehicles'] });
    },
    onError: (e) => setError(localizeError(e, t)),
  });

  const canCreate = Boolean(me.data) && registration.trim() && capacity;

  return (
    <div className="space-y-5">
      <h1 className="text-h1 text-fg">{t('org:vehicles.title')}</h1>

      <Card>
        <h2 className="text-label text-fg-secondary">{t('org:vehicles.createTitle')}</h2>
        {!me.data && (
          <div className="mt-2">
            <Alert tone="warning">{t('org:groups.needProfile')}</Alert>
          </div>
        )}
        <form
          className="mt-3 grid gap-3 sm:grid-cols-2"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            if (canCreate) create.mutate();
          }}
        >
          <label className="text-body-sm">
            <span className="mb-1 block font-medium text-fg-secondary">{t('org:vehicles.class')}</span>
            <select
              className="min-h-target w-full rounded-md border border-line-strong bg-surface-input px-2 text-body-sm text-fg"
              value={vehicleClass}
              onChange={(e) => setVehicleClass(e.target.value)}
            >
              {VEHICLE_CLASSES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
          <Field label={t('org:vehicles.registration')}>
            {({ id }) => (
              <Input
                id={id}
                value={registration}
                onChange={(e) => setRegistration(e.target.value)}
                placeholder="KAA 123A"
              />
            )}
          </Field>
          <Field label={t('org:vehicles.capacity')}>
            {({ id }) => (
              <Input
                id={id}
                type="number"
                min="0"
                value={capacity}
                onChange={(e) => setCapacity(e.target.value)}
              />
            )}
          </Field>
          <label className="text-body-sm">
            <span className="mb-1 block font-medium text-fg-secondary">{t('org:vehicles.unit')}</span>
            <select
              className="min-h-target w-full rounded-md border border-line-strong bg-surface-input px-2 text-body-sm text-fg"
              value={unit}
              onChange={(e) => setUnit(e.target.value)}
            >
              {CAPACITY_UNITS.map((u) => (
                <option key={u} value={u}>
                  {u}
                </option>
              ))}
            </select>
          </label>
          {manageableGroups.length > 0 && (
            <label className="text-body-sm sm:col-span-2">
              <span className="mb-1 block font-medium text-fg-secondary">
                {t('org:vehicles.toGroup')}
              </span>
              <select
                className="min-h-target w-full rounded-md border border-line-strong bg-surface-input px-2 text-body-sm text-fg"
                value={groupId}
                onChange={(e) => setGroupId(e.target.value)}
              >
                <option value="">— {t('org:nav.operator')} —</option>
                {manageableGroups.map((g) => (
                  <option key={g.id} value={g.id}>
                    {g.name}
                  </option>
                ))}
              </select>
            </label>
          )}
          <div className="sm:col-span-2">
            <Button type="submit" loading={create.isPending} disabled={!canCreate}>
              {t('org:common.create')}
            </Button>
          </div>
        </form>
        {error && (
          <div className="mt-3">
            <Alert tone="danger">{error}</Alert>
          </div>
        )}
      </Card>

      {list.isLoading ? (
        <PageLoader />
      ) : list.isError ? (
        <ErrorState message={localizeError(list.error, t)} onRetry={() => void list.refetch()} />
      ) : list.data && list.data.data.length > 0 ? (
        <ul className="space-y-2">
          {list.data.data.map((v) => (
            <li key={v.id}>
              <Link to={`/vehicles/${v.id}`} className="block rounded-md">
                <Card interactive>
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-semibold text-fg">
                      {v.registration} · {v.vehicle_class}
                    </span>
                    <span className="flex items-center gap-2">
                      {v.vehicle_class_heavy && (
                        <StatusBadge tone="brand" label={t('org:vehicles.heavy')} />
                      )}
                      <StatusBadge label={v.controller_kind} />
                      <StatusBadge {...vehicleStatusBadge(v.status)} />
                    </span>
                  </div>
                </Card>
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState title={t('org:vehicles.empty')} />
      )}
    </div>
  );
}
