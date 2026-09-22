import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ErrorState } from '@/components/ErrorState';
import { PageLoader } from '@/components/PageLoader';
import { useAuth } from '@/features/auth/useAuth';
import { jobReference } from '@/features/jobs/jobHelpers';
import { jobsApi } from '@/features/jobs/jobsApi';
import { formatKes, parseKesToMinorUnits } from '@/features/jobs/money';
import { localizeError } from '@/services/errorMessage';

import { disputesApi, incidentsApi } from './incidentsApi';
import {
  COMMISSION_TREATMENTS,
  ROUTABLE_JOB_STATUSES,
  RESOLUTION_OUTCOMES,
  type CommissionTreatment,
  type ResolutionOutcome,
  type RoutableJobStatus,
} from './types';

/**
 * DisputeDetailPage — §17.2 (Ops Officer review, amicable-first) / §17.3
 * (Platform Admin binding resolution + the disabled `DISPUTED → RESUME`
 * shell). Band gating (Ops Officer STANDARD-only, Platform-Admin-only
 * above STANDARD, REDUCE/WAIVE Platform-Admin-only) mirrors exactly what
 * the backend's `AdminBandAuthorised` guard and `can_adjust_commission`
 * already enforce server-side — this is UX only, never the real gate.
 */
export function DisputeDetailPage(): JSX.Element {
  const { disputeId } = useParams<{ disputeId: string }>();
  const { t } = useTranslation(['incidents', 'jobs', 'errors']);
  const qc = useQueryClient();
  const { user } = useAuth();
  const isAdminViewer = Boolean(user?.is_admin);
  const isPlatformAdmin = Boolean(user?.roles.includes('PLATFORM_ADMIN'));

  const [outcomeCode, setOutcomeCode] = useState<ResolutionOutcome>('ADMIN_DETERMINATION');
  const [rationale, setRationale] = useState('');
  const [routedStatus, setRoutedStatus] = useState<RoutableJobStatus>('COMPLETED');
  const [commissionTreatment, setCommissionTreatment] = useState<CommissionTreatment>('APPLY');
  const [reducedAmount, setReducedAmount] = useState('');

  const dispute = useQuery({
    queryKey: ['disputes-detail', disputeId],
    queryFn: () => disputesApi.get(disputeId!),
    enabled: !!disputeId,
    retry: false,
  });
  const job = useQuery({
    queryKey: ['jobs', dispute.data?.job_id],
    queryFn: () => jobsApi.get(dispute.data!.job_id),
    enabled: !!dispute.data,
    retry: false,
  });
  const incidentsForJob = useQuery({
    queryKey: ['incidents', dispute.data?.job_id],
    queryFn: () => incidentsApi.listForJob(dispute.data!.job_id),
    enabled: !!dispute.data,
    retry: false,
  });

  const resolve = useMutation({
    mutationFn: () => {
      const reduced = parseKesToMinorUnits(reducedAmount);
      return disputesApi.resolve(
        disputeId!,
        {
          outcome_code: outcomeCode,
          rationale,
          routed_job_status: routedStatus,
          commission_treatment: isPlatformAdmin ? commissionTreatment : 'APPLY',
          reduced_amount_kes:
            isPlatformAdmin && commissionTreatment === 'REDUCE' && reduced ? reduced : undefined,
        },
        crypto.randomUUID(),
      );
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['disputes-detail', disputeId] });
      void qc.invalidateQueries({ queryKey: ['jobs', dispute.data?.job_id] });
      // Shares its key with `JobDetailPage`'s own dispute lookup — keep it
      // consistent in case a later dispute reopens on the same job.
      void qc.invalidateQueries({ queryKey: ['disputes', dispute.data?.job_id] });
    },
  });

  if (dispute.isLoading || (dispute.data && (job.isLoading || incidentsForJob.isLoading))) {
    return <PageLoader />;
  }
  if (dispute.isError || !dispute.data) {
    return (
      <ErrorState message={localizeError(dispute.error, t)} onRetry={() => void dispute.refetch()} />
    );
  }
  const d = dispute.data;
  const isStandardBand = job.data?.value_band === 'STANDARD';
  const linkedIncidents = incidentsForJob.data?.data.filter((i) => d.incident_ids.includes(i.id)) ?? [];
  const isResolved = d.resolution !== null;
  const canResolveHere = isAdminViewer && !isResolved && (isStandardBand || isPlatformAdmin);
  const needsPlatformAdmin = isAdminViewer && !isResolved && !isStandardBand && !isPlatformAdmin;

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <div>
        <h1 className="text-h1 text-fg">{t('dispute.title')}</h1>
        <p className="text-body-sm text-fg-secondary">{t(`detail.status.${d.status}`)}</p>
      </div>

      <Card className="space-y-2">
        <h2 className="text-label text-fg-secondary">{t('detail.jobContext')}</h2>
        <p className="text-body text-fg">{t('detail.jobRef', { ref: jobReference(d.job_id) })}</p>
        <p className="text-body-sm text-fg-secondary">{t('dispute.preDisputeStatus', { status: d.pre_dispute_status })}</p>
        <Link to={`/jobs/${d.job_id}`} className="text-body-sm text-action-secondary-text underline">
          {t('detail.viewJob')}
        </Link>
      </Card>

      <Card className="space-y-2">
        <h2 className="text-label text-fg-secondary">{t('dispute.linkedIncidents')}</h2>
        {linkedIncidents.length === 0 ? (
          <p className="text-body-sm text-fg-muted">{t('dispute.noLinkedIncidents')}</p>
        ) : (
          <ul className="space-y-1">
            {linkedIncidents.map((i) => (
              <li key={i.id}>
                <Link to={`/incidents/${i.id}`} className="text-body-sm text-action-secondary-text underline">
                  {t(`report.type.${i.type}`)}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {d.resolution && (
        <Card className="space-y-1">
          <h2 className="text-label text-fg-secondary">{t('dispute.resolution.title')}</h2>
          <p className="text-body text-fg">
            {t('dispute.resolution.outcome', {
              status: t(`jobs:status.${d.resolution.routed_job_status}`),
            })}
          </p>
          <p className="text-body-sm text-fg-secondary">{d.resolution.rationale}</p>
        </Card>
      )}

      {!isAdminViewer && !d.resolution && <Alert tone="info">{t('dispute.underReview')}</Alert>}

      {needsPlatformAdmin && (
        <Alert tone="warning">
          {t('dispute.needsPlatformAdmin')}
          {linkedIncidents[0] && (
            <>
              {' '}
              <Link to={`/incidents/${linkedIncidents[0].id}`} className="underline">
                {t('dispute.escalateToAdmin')}
              </Link>
            </>
          )}
        </Alert>
      )}

      {canResolveHere && (
        <Card className="space-y-3">
          <h2 className="text-label text-fg-secondary">{t('dispute.resolve.title')}</h2>

          <label className="block space-y-1">
            <span className="text-label text-fg-secondary">{t('dispute.resolve.outcome')}</span>
            <select
              value={outcomeCode}
              onChange={(e) => setOutcomeCode(e.target.value as ResolutionOutcome)}
              className="min-h-target w-full rounded-md border border-line-strong bg-surface-input px-3 text-body text-fg"
            >
              {RESOLUTION_OUTCOMES.map((o) => (
                <option key={o} value={o}>
                  {t(`dispute.resolve.outcomes.${o}`)}
                </option>
              ))}
            </select>
          </label>

          <label className="block space-y-1">
            <span className="text-label text-fg-secondary">{t('dispute.resolve.routedStatus')}</span>
            <select
              value={routedStatus}
              onChange={(e) => setRoutedStatus(e.target.value as RoutableJobStatus)}
              className="min-h-target w-full rounded-md border border-line-strong bg-surface-input px-3 text-body text-fg"
            >
              {ROUTABLE_JOB_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {t(`jobs:status.${s}`)}
                </option>
              ))}
            </select>
          </label>

          {isPlatformAdmin && (
            <label className="block space-y-1">
              <span className="text-label text-fg-secondary">{t('dispute.resolve.commissionTreatment')}</span>
              <select
                value={commissionTreatment}
                onChange={(e) => setCommissionTreatment(e.target.value as CommissionTreatment)}
                className="min-h-target w-full rounded-md border border-line-strong bg-surface-input px-3 text-body text-fg"
              >
                {COMMISSION_TREATMENTS.map((c) => (
                  <option key={c} value={c}>
                    {t(`dispute.resolve.commissionTreatments.${c}`)}
                  </option>
                ))}
              </select>
            </label>
          )}

          {isPlatformAdmin && commissionTreatment === 'REDUCE' && (
            <label className="block space-y-1">
              <span className="text-label text-fg-secondary">{t('dispute.resolve.reducedAmount')}</span>
              <input
                inputMode="decimal"
                value={reducedAmount}
                onChange={(e) => setReducedAmount(e.target.value)}
                placeholder={formatKes(0)}
                className="min-h-target w-full rounded-md border border-line-strong bg-surface-input px-3 text-body text-fg"
              />
            </label>
          )}

          <textarea
            aria-label={t('dispute.resolve.rationale')}
            placeholder={t('dispute.resolve.rationale')}
            value={rationale}
            onChange={(e) => setRationale(e.target.value)}
            className="min-h-[80px] w-full rounded-md border border-line-strong bg-surface-input px-3 py-2 text-body text-fg"
          />

          <Button
            disabled={!rationale.trim()}
            loading={resolve.isPending}
            onClick={() => resolve.mutate()}
          >
            {t('dispute.resolve.apply')}
          </Button>

          {resolve.isError && <Alert tone="danger">{localizeError(resolve.error, t)}</Alert>}
        </Card>
      )}

      {isPlatformAdmin && !isResolved && (
        <Card className="space-y-2">
          <h2 className="text-label text-fg-secondary">
            {t('dispute.resume.title', { status: t(`jobs:status.${d.pre_dispute_status}`) })}
          </h2>
          <textarea
            aria-label={t('dispute.resume.reason')}
            placeholder={t('dispute.resume.reason')}
            disabled
            className="min-h-[60px] w-full rounded-md border border-line-strong bg-surface-sunken px-3 py-2 text-body text-fg-disabled"
          />
          <Button disabled fullWidth>
            {t('dispute.resume.action', { status: t(`jobs:status.${d.pre_dispute_status}`) })}
          </Button>
          <p className="text-body-sm text-fg-muted">{t('dispute.resume.notAvailable')}</p>
        </Card>
      )}
    </div>
  );
}
