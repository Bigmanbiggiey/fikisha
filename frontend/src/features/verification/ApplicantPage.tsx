import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ErrorState } from '@/components/ErrorState';
import { Input } from '@/components/Input';
import { PageLoader } from '@/components/PageLoader';
import { StatusBadge } from '@/components/StatusBadge';
import { VerificationPill } from '@/components/VerificationPill';
import type { VerificationState } from '@/design/tokens';
import { StaffTierPanel } from '@/features/trust/StaffTierPanel';
import { formatDateTime } from '@/services/datetime';
import { localizeError } from '@/services/errorMessage';

import { RecordReview } from './RecordReview';
import { verificationApi, type ApplicantAsset, type ApplicantKind } from './verificationApi';

/**
 * Everything one applicant submitted, on one screen (assessment 2026-10-19
 * part 5): their details, then each record (documents, review actions,
 * history), grouped by what it is about: the applicant themselves, each
 * vehicle, each operating location. For a pending operator, the Approve
 * action (D-2) sits at the top.
 */
export function ApplicantPage(): JSX.Element {
  const { kind = 'OPERATOR', applicantId = '' } = useParams();
  const { t } = useTranslation(['org', 'errors']);
  const qc = useQueryClient();
  const key = ['verification-applicants', kind, applicantId];
  const detail = useQuery({
    queryKey: key,
    queryFn: () => verificationApi.applicant(kind as ApplicantKind, applicantId),
    retry: false,
  });

  const [note, setNote] = useState('');
  const [error, setError] = useState<string | null>(null);
  const approve = useMutation({
    mutationFn: () => verificationApi.approveOperator(applicantId, note.trim()),
    onSuccess: () => {
      setError(null);
      void qc.invalidateQueries({ queryKey: ['verification-applicants'] });
    },
    onError: (e) => setError(localizeError(e, t)),
  });

  if (detail.isLoading) return <PageLoader />;
  if (detail.isError || !detail.data) {
    return (
      <ErrorState message={localizeError(detail.error, t)} error={detail.error} onRetry={() => void detail.refetch()} />
    );
  }
  const a = detail.data;
  const refresh = [key, ['verification-applicants', kind]];

  return (
    <div className="space-y-5">
      <Link to={`/verification?kind=${a.kind}`} className="text-body-sm text-action-secondary-text">
        &larr; {t('org:common.back')}
      </Link>

      <Card>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h1 className="text-h1 text-fg">{a.name}</h1>
          <span className="flex flex-wrap gap-2">
            <StatusBadge tone="neutral" label={t(`org:applicants.tab.${a.kind}`)} />
            <StatusBadge
              tone={a.status === 'ACTIVE' || a.status === 'VERIFIED' ? 'success' : 'warning'}
              label={t(`org:applicants.status.${a.status}`, { defaultValue: a.status })}
            />
          </span>
        </div>
        <dl className="mt-3 space-y-1 text-body-sm">
          {a.full_name && a.full_name !== a.name && <Row label={t('org:operator.fullName')} value={a.full_name} />}
          {a.category && <Row label={t('org:business.category')} value={a.category} />}
          {a.group_type && <Row label={t('org:applicants.groupType')} value={a.group_type} />}
          {a.member_count !== undefined && (
            <Row label={t('org:business.members')} value={String(a.member_count)} />
          )}
          <Row label={t('org:applicants.registered')} value={formatDateTime(a.created_at)} />
        </dl>

        {a.requirements && (
          <>
            <h2 className="mt-3 text-label text-fg-secondary">{t('org:applicants.checksTitle')}</h2>
            <ul className="mt-1 flex flex-wrap gap-2">
              {a.requirements
                .filter((r) => r.mandatory)
                .map((r) => (
                  <li key={r.domain}>
                    <VerificationPill
                      state={r.state as VerificationState}
                      groupLabel={t(`org:operatorApproval.domain.${r.domain}`, { defaultValue: r.domain })}
                    />
                  </li>
                ))}
            </ul>
          </>
        )}

        {a.kind === 'OPERATOR' && a.status === 'PENDING' && (
          <div className="mt-4 space-y-2 rounded-md bg-surface-sunken p-3">
            <h2 className="text-h3 text-fg">{t('org:applicants.approveTitle')}</h2>
            <p className="text-body-sm text-fg-secondary">{t('org:applicants.approveBody')}</p>
            {a.verified_count !== a.required_count && (
              <Alert tone="warning">
                {t('org:applicants.notAllVerified', { done: a.verified_count, total: a.required_count })}
              </Alert>
            )}
            <Input
              aria-label={t('org:verification.note')}
              placeholder={t('org:verification.note')}
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
            <Button onClick={() => approve.mutate()} loading={approve.isPending}>
              {t('org:applicants.approveOperator')}
            </Button>
            {error && <Alert tone="danger">{error}</Alert>}
          </div>
        )}
        {a.kind === 'OPERATOR' && a.status === 'ACTIVE' && (
          <p className="mt-3 text-body-sm text-status-success-fg">{t('org:applicants.approved')}</p>
        )}
      </Card>

      {a.kind === 'OPERATOR' && a.status !== 'PENDING' && <StaffTierPanel operatorId={applicantId} />}

      <section className="space-y-3" aria-labelledby="own-records">
        <h2 id="own-records" className="text-h2 text-fg">
          {t(`org:applicants.ownRecords.${a.kind}`)}
        </h2>
        {a.records.length === 0 ? (
          <p className="text-body-sm text-fg-muted">{t('org:verification.noRecords')}</p>
        ) : (
          a.records.map((r) => (
            <RecordReview
              key={r.id}
              record={r}
              refresh={refresh}
              heading={t(`org:applicants.domain.${r.domain}`, { defaultValue: r.domain })}
            />
          ))
        )}
      </section>

      {a.locations && (
        <Card>
          <h2 className="text-h3 text-fg">{t('org:business.locations')}</h2>
          {a.locations.length === 0 ? (
            <Alert tone="warning">{t('org:applicants.noLocations')}</Alert>
          ) : (
            <ul className="mt-2 divide-y divide-line text-body-sm">
              {a.locations.map((l) => (
                <li key={l.id} className="py-2">
                  <span className="font-medium text-fg">{l.label}</span>
                  <span className="text-fg-muted">
                    {' '}
                    · {l.type}
                    {l.address_text ? ` · ${l.address_text}` : ''}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      )}

      {a.vehicles && (
        <AssetSection
          title={t('org:applicants.vehicles')}
          empty={t('org:applicants.noVehicles')}
          assets={a.vehicles}
          label={(v) => `${v.registration ?? ''} · ${v.vehicle_class ?? ''}`}
          refresh={refresh}
        />
      )}
      {a.bases && a.bases.length > 0 && (
        <AssetSection
          title={t('org:nav.locations')}
          empty=""
          assets={a.bases}
          label={(b) => `${b.name ?? ''} · ${b.type ?? ''}`}
          refresh={refresh}
        />
      )}
    </div>
  );
}

function AssetSection({
  title,
  empty,
  assets,
  label,
  refresh,
}: {
  title: string;
  empty: string;
  assets: ApplicantAsset[];
  label: (a: ApplicantAsset) => string;
  refresh: unknown[][];
}): JSX.Element {
  const { t } = useTranslation('org');
  return (
    <section className="space-y-3">
      <h2 className="text-h2 text-fg">{title}</h2>
      {assets.length === 0 && <p className="text-body-sm text-fg-muted">{empty}</p>}
      {assets.map((asset) => (
        <div key={asset.id} className="space-y-2">
          <h3 className="text-h3 text-fg">{label(asset)}</h3>
          {asset.records.length === 0 ? (
            <p className="text-body-sm text-fg-muted">{t('verification.noRecords')}</p>
          ) : (
            asset.records.map((r) => (
              <RecordReview
                key={r.id}
                record={r}
                refresh={refresh}
                heading={t(`applicants.domain.${r.domain}`, { defaultValue: r.domain })}
              />
            ))
          )}
        </div>
      ))}
    </section>
  );
}

function Row({ label, value }: { label: string; value: string }): JSX.Element {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-fg-muted">{label}</dt>
      <dd className="font-medium text-fg">{value}</dd>
    </div>
  );
}
