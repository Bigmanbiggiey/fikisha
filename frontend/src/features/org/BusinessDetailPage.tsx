import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ErrorState } from '@/components/ErrorState';
import { Field } from '@/components/Field';
import { Input } from '@/components/Input';
import { PageLoader } from '@/components/PageLoader';
import { StatusBadge } from '@/components/StatusBadge';
import { localizeError } from '@/services/errorMessage';

import { orgApi } from './orgApi';
import { BUSINESS_ROLES, LOCATION_TYPES } from './types';

export function BusinessDetailPage(): JSX.Element {
  const { businessId = '' } = useParams();
  const { t } = useTranslation(['org', 'errors']);
  const qc = useQueryClient();

  const biz = useQuery({
    queryKey: ['business', businessId],
    queryFn: () => orgApi.getBusiness(businessId),
    retry: false,
  });
  const members = useQuery({
    queryKey: ['business', businessId, 'members'],
    queryFn: () => orgApi.listMembers(businessId),
    enabled: biz.isSuccess,
    retry: false,
  });
  const locations = useQuery({
    queryKey: ['business', businessId, 'locations'],
    queryFn: () => orgApi.listLocations(businessId),
    enabled: biz.isSuccess,
    retry: false,
  });

  const isOwner = biz.data?.my_role === 'OWNER';
  const canManageLocations = isOwner || biz.data?.my_role === 'DISPATCHER';

  const [contactPhone, setContactPhone] = useState('');
  const saveProfile = useMutation({
    mutationFn: () => orgApi.updateBusiness(businessId, { contact_phone: contactPhone.trim() }),
    onSuccess: () => {
      setContactPhone('');
      void qc.invalidateQueries({ queryKey: ['business', businessId] });
    },
  });

  const [memberPhone, setMemberPhone] = useState('');
  const [memberRole, setMemberRole] = useState<string>('DISPATCHER');
  const [memberError, setMemberError] = useState<string | null>(null);
  const addMember = useMutation({
    mutationFn: () => orgApi.addMember(businessId, { phone: memberPhone.trim(), role: memberRole }),
    onSuccess: () => {
      setMemberPhone('');
      setMemberError(null);
      void qc.invalidateQueries({ queryKey: ['business', businessId, 'members'] });
    },
    onError: (err) => setMemberError(localizeError(err, t)),
  });

  const [locLabel, setLocLabel] = useState('');
  const [locType, setLocType] = useState<string>('BRANCH');
  const [locError, setLocError] = useState<string | null>(null);
  const addLocation = useMutation({
    mutationFn: () => orgApi.addLocation(businessId, { label: locLabel.trim(), type: locType }),
    onSuccess: () => {
      setLocLabel('');
      setLocError(null);
      void qc.invalidateQueries({ queryKey: ['business', businessId, 'locations'] });
    },
    onError: (err) => setLocError(localizeError(err, t)),
  });

  if (biz.isLoading) return <PageLoader />;
  if (biz.isError || !biz.data) {
    return <ErrorState message={localizeError(biz.error, t)} onRetry={() => void biz.refetch()} />;
  }

  return (
    <div className="space-y-5">
      <Link to="/businesses" className="text-body-sm text-action-secondary-text">
        &larr; {t('org:common.back')}
      </Link>

      <Card>
        <div className="flex items-center justify-between gap-3">
          <h1 className="text-h1 text-fg">{biz.data.trading_name}</h1>
          <span className="flex flex-wrap gap-2">
            {biz.data.my_role && <StatusBadge tone="brand" label={biz.data.my_role} />}
            <StatusBadge
              tone={biz.data.standing === 'GOOD' ? 'success' : 'danger'}
              icon={biz.data.standing === 'GOOD' ? 'check' : 'alert'}
              label={biz.data.standing}
            />
          </span>
        </div>
        <dl className="mt-3 space-y-1 text-body-sm">
          <Row label={t('org:business.contactPhone')} value={biz.data.contact_phone || '—'} />
          <Row label={t('org:business.contactEmail')} value={biz.data.contact_email || '—'} />
        </dl>

        {isOwner && (
          <form
            className="mt-4 flex flex-col gap-3 border-t border-line pt-4 sm:flex-row sm:items-end"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              if (contactPhone.trim()) saveProfile.mutate();
            }}
          >
            <div className="flex-1">
              <Field label={t('org:business.contactPhone')}>
                {({ id }) => (
                  <Input
                    id={id}
                    value={contactPhone}
                    onChange={(e) => setContactPhone(e.target.value)}
                    placeholder={biz.data.contact_phone}
                  />
                )}
              </Field>
            </div>
            <Button type="submit" variant="secondary" loading={saveProfile.isPending}>
              {t('org:common.save')}
            </Button>
          </form>
        )}
      </Card>

      <Card>
        <h2 className="text-label text-fg-secondary">{t('org:business.members')}</h2>
        <ul className="mt-2 divide-y divide-line text-body-sm">
          {(members.data?.data ?? []).map((m) => (
            <li key={m.id} className="flex items-center justify-between py-2">
              <span>{m.user_display_name || m.user_phone}</span>
              <span className="flex items-center gap-2">
                <StatusBadge tone="brand" label={m.role} />
                <StatusBadge
                  tone={m.status === 'ACTIVE' ? 'success' : 'neutral'}
                  icon={m.status === 'ACTIVE' ? 'check' : undefined}
                  label={m.status}
                />
                {isOwner && m.status === 'ACTIVE' && (
                  <Button
                    variant="destructive"
                    size="compact"
                    onClick={() =>
                      orgApi
                        .removeMember(businessId, m.id)
                        .then(() =>
                          qc.invalidateQueries({ queryKey: ['business', businessId, 'members'] }),
                        )
                        .catch(() => undefined)
                    }
                  >
                    {t('org:common.remove')}
                  </Button>
                )}
              </span>
            </li>
          ))}
        </ul>

        {isOwner && (
          <form
            className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-end"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              if (memberPhone.trim()) addMember.mutate();
            }}
          >
            <div className="flex-1">
              <Field label={t('org:business.memberPhone')}>
                {({ id }) => (
                  <Input
                    id={id}
                    value={memberPhone}
                    onChange={(e) => setMemberPhone(e.target.value)}
                  />
                )}
              </Field>
            </div>
            <select
              className="min-h-target rounded-md border border-line-strong bg-surface-input px-2 text-body-sm text-fg"
              value={memberRole}
              onChange={(e) => setMemberRole(e.target.value)}
            >
              {BUSINESS_ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
            <Button type="submit" loading={addMember.isPending}>
              {t('org:common.add')}
            </Button>
          </form>
        )}
        {memberError && (
          <div className="mt-2">
            <Alert tone="danger">{memberError}</Alert>
          </div>
        )}
      </Card>

      <Card>
        <h2 className="text-label text-fg-secondary">{t('org:business.locations')}</h2>
        <p className="mt-1 text-caption text-fg-muted">{t('org:business.mainLocationNote')}</p>
        <ul className="mt-2 divide-y divide-line text-body-sm">
          {(locations.data?.data ?? []).map((l) => (
            <li key={l.id} className="flex items-center justify-between py-2">
              <span>
                {l.label}
                {l.zone_code ? ` · ${l.zone_code}` : ''}
              </span>
              <span className="flex items-center gap-2">
                <StatusBadge
                  tone={l.type === 'MAIN' ? 'success' : 'neutral'}
                  icon={l.type === 'MAIN' ? 'check' : undefined}
                  label={l.type}
                />
                {canManageLocations && (
                  <Button
                    variant="destructive"
                    size="compact"
                    onClick={() =>
                      orgApi
                        .removeLocation(businessId, l.id)
                        .then(() =>
                          qc.invalidateQueries({
                            queryKey: ['business', businessId, 'locations'],
                          }),
                        )
                        .catch(() => undefined)
                    }
                  >
                    {t('org:common.remove')}
                  </Button>
                )}
              </span>
            </li>
          ))}
        </ul>

        {canManageLocations && (
          <form
            className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-end"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              if (locLabel.trim()) addLocation.mutate();
            }}
          >
            <div className="flex-1">
              <Field label={t('org:business.locationLabel')}>
                {({ id }) => (
                  <Input id={id} value={locLabel} onChange={(e) => setLocLabel(e.target.value)} />
                )}
              </Field>
            </div>
            <select
              className="min-h-target rounded-md border border-line-strong bg-surface-input px-2 text-body-sm text-fg"
              value={locType}
              onChange={(e) => setLocType(e.target.value)}
            >
              {LOCATION_TYPES.map((ty) => (
                <option key={ty} value={ty}>
                  {ty}
                </option>
              ))}
            </select>
            <Button type="submit" loading={addLocation.isPending}>
              {t('org:common.add')}
            </Button>
          </form>
        )}
        {locError && (
          <div className="mt-2">
            <Alert tone="danger">{locError}</Alert>
          </div>
        )}
      </Card>
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
