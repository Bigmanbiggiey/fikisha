import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ErrorState } from '@/components/ErrorState';
import { Field } from '@/components/Field';
import { PageLoader } from '@/components/PageLoader';
import { PhoneInput } from '@/components/PhoneInput';
import { StatusBadge } from '@/components/StatusBadge';
import { Select } from '@/components/Select';
import { ORGANISATION_EVIDENCE_KINDS } from '@/features/verification/verificationApi';
import { VerificationPanel } from '@/features/verification/VerificationPanel';
import { localizeError } from '@/services/errorMessage';
import { displayPhone, isValidKenyanPhone } from '@/services/phone';

import { BusinessLocationsCard } from './BusinessLocationsCard';
import { BusinessVerificationBanner } from './BusinessVerificationBanner';
import { orgApi } from './orgApi';
import { BUSINESS_ROLES } from './types';

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

  if (biz.isLoading) return <PageLoader />;
  if (biz.isError || !biz.data) {
    return <ErrorState message={localizeError(biz.error, t)} error={biz.error} onRetry={() => void biz.refetch()} />;
  }

  return (
    <div className="space-y-5">
      <Link to="/businesses" className="text-body-sm text-action-secondary-text">
        &larr; {t('org:common.back')}
      </Link>

      <BusinessVerificationBanner businessId={businessId} showLink={false} />
      {biz.data.verification_status !== 'VERIFIED' && locations.data?.data.length === 0 && (
        <Alert tone="warning">{t('org:businessVerification.needsLocation')}</Alert>
      )}

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
            className="mt-4 flex flex-col gap-3 border-t border-line pt-4 md:flex-row md:items-end"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              if (isValidKenyanPhone(contactPhone)) saveProfile.mutate();
            }}
          >
            <div className="flex-1">
              <Field label={t('org:business.contactPhone')}>
                {({ id }) => (
                  <PhoneInput
                    id={id}
                    value={contactPhone}
                    onChange={setContactPhone}
                    placeholder={displayPhone(biz.data.contact_phone)}
                  />
                )}
              </Field>
            </div>
            <Button
              type="submit"
              variant="secondary"
              loading={saveProfile.isPending}
              disabled={!isValidKenyanPhone(contactPhone)}
            >
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
              <span>{m.user_display_name || displayPhone(m.user_phone)}</span>
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
            className="mt-3 flex flex-col gap-2 md:flex-row md:items-end"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              if (isValidKenyanPhone(memberPhone)) addMember.mutate();
            }}
          >
            <div className="flex-1">
              <Field label={t('org:business.memberPhone')}>
                {({ id }) => (
                  <PhoneInput id={id} value={memberPhone} onChange={setMemberPhone} />
                )}
              </Field>
            </div>
            <Select
              inline
              aria-label={t('org:common.role')}
              value={memberRole}
              onChange={(e) => setMemberRole(e.target.value)}
            >
              {BUSINESS_ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </Select>
            <Button type="submit" loading={addMember.isPending} disabled={!isValidKenyanPhone(memberPhone)}>
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

      <BusinessLocationsCard
        businessId={businessId}
        locations={locations.data?.data ?? []}
        canManage={canManageLocations}
      />

      {/* The owner submits (or resubmits) the business's details; documents
          are optional (D-1). */}
      {isOwner && (
        <VerificationPanel
          subjectType="BUSINESS"
          subjectId={businessId}
          kinds={ORGANISATION_EVIDENCE_KINDS}
          documentsOptional
        />
      )}
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
