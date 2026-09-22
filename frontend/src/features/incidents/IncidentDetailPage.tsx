import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ErrorState } from '@/components/ErrorState';
import { PageLoader } from '@/components/PageLoader';
import { useAuth } from '@/features/auth/useAuth';
import { jobReference } from '@/features/jobs/jobHelpers';
import { localizeError } from '@/services/errorMessage';

import { disputesApi, incidentsApi } from './incidentsApi';

/**
 * IncidentDetailPage — §17.2 "Incident / dispute review". Reachable right
 * after reporting (before any dispute exists) and by direct link
 * thereafter — there is no cross-job queue this increment (Decision 3 in
 * the plan; that's Increment 8's job monitoring table). Job route/actor/
 * timeline context is deliberately not re-rendered here — a summary +
 * link to the existing `/jobs/:jobId` page is reused instead.
 */
export function IncidentDetailPage(): JSX.Element {
  const { incidentId } = useParams<{ incidentId: string }>();
  const { t } = useTranslation(['incidents', 'errors']);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { user } = useAuth();
  // "Any admin" (Ops Officer or Platform Admin both carry an AdminProfile,
  // hence `is_admin`) vs "Platform-Admin-only" — the same split the backend
  // itself enforces (D-ADM-1); `roles` distinguishes which admin tier.
  const isAdminViewer = Boolean(user?.is_admin);
  const isPlatformAdmin = Boolean(user?.roles.includes('PLATFORM_ADMIN'));

  const [statementText, setStatementText] = useState('');
  const [escalateReason, setEscalateReason] = useState('');
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const incident = useQuery({
    queryKey: ['incidents', incidentId],
    queryFn: () => incidentsApi.get(incidentId!),
    enabled: !!incidentId,
    retry: false,
  });

  const disputes = useQuery({
    queryKey: ['disputes', incident.data?.job_id],
    queryFn: () => disputesApi.listForJob(incident.data!.job_id),
    enabled: !!incident.data,
    retry: false,
  });

  function invalidate(): void {
    void qc.invalidateQueries({ queryKey: ['incidents', incidentId] });
  }

  const startReview = useMutation({
    mutationFn: () => incidentsApi.startReview(incidentId!),
    onSuccess: invalidate,
  });
  const startAmicable = useMutation({
    mutationFn: () => incidentsApi.startAmicable(incidentId!),
    onSuccess: invalidate,
  });
  const openDispute = useMutation({
    mutationFn: () => disputesApi.open(incident.data!.job_id, [incidentId!], crypto.randomUUID()),
    onSuccess: (res) => {
      // `JobDetailPage` reads this exact same query key once the job is
      // DISPUTED — without invalidating it here, its pre-dispute empty
      // result (cached for the default 30s staleTime) leaks through and
      // "View dispute" silently falls back to its no-dispute-found state.
      // Found live (Design Phase 6 Increment 7 verification).
      void qc.invalidateQueries({ queryKey: ['disputes', incident.data!.job_id] });
      void qc.invalidateQueries({ queryKey: ['jobs', incident.data!.job_id] });
      navigate(`/disputes/${res.dispute.id}`);
    },
  });
  const escalate = useMutation({
    mutationFn: () => incidentsApi.escalate(incidentId!, escalateReason),
    onSuccess: () => {
      setEscalateReason('');
      invalidate();
    },
  });
  const addStatement = useMutation({
    mutationFn: () => incidentsApi.addStatement(incidentId!, statementText),
    onSuccess: () => {
      setStatementText('');
      invalidate();
    },
  });

  async function downloadEvidence(evidenceRowId: string): Promise<void> {
    try {
      const blob = await incidentsApi.evidenceBlob(evidenceRowId);
      window.open(URL.createObjectURL(blob), '_blank', 'noopener');
    } catch (e) {
      setDownloadError(localizeError(e, t));
    }
  }

  if (incident.isLoading) return <PageLoader />;
  if (incident.isError || !incident.data) {
    return (
      <ErrorState message={localizeError(incident.error, t)} onRetry={() => void incident.refetch()} />
    );
  }
  const inc = incident.data;
  const linkedDispute = disputes.data?.data.find((d) => d.incident_ids.includes(inc.id));
  const canAct = inc.status !== 'RESOLVED';

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <div>
        <h1 className="text-h1 text-fg">{t(`report.type.${inc.type}`)}</h1>
        <p className="text-body-sm text-fg-secondary">{t(`detail.status.${inc.status}`)}</p>
      </div>

      <Card className="space-y-2">
        <h2 className="text-label text-fg-secondary">{t('detail.jobContext')}</h2>
        <p className="text-body text-fg">{t('detail.jobRef', { ref: jobReference(inc.job_id) })}</p>
        <Link to={`/jobs/${inc.job_id}`} className="text-body-sm text-action-secondary-text underline">
          {t('detail.viewJob')}
        </Link>
      </Card>

      {inc.description && (
        <Card>
          <h2 className="text-label text-fg-secondary">{t('detail.description')}</h2>
          <p className="mt-2 text-body text-fg">{inc.description}</p>
        </Card>
      )}

      <Card className="space-y-3">
        <h2 className="text-label text-fg-secondary">{t('detail.evidence')}</h2>
        {inc.evidence.length === 0 ? (
          <p className="text-body-sm text-fg-muted">{t('detail.noEvidence')}</p>
        ) : (
          <ul className="space-y-2">
            {inc.evidence.map((e) => (
              <li key={e.id}>
                <Button variant="secondary" size="compact" onClick={() => void downloadEvidence(e.id)}>
                  {e.caption || t('detail.evidenceItem')}
                </Button>
              </li>
            ))}
          </ul>
        )}
        {downloadError && <Alert tone="danger">{downloadError}</Alert>}
      </Card>

      <Card className="space-y-3">
        <h2 className="text-label text-fg-secondary">{t('detail.statements')}</h2>
        {inc.statements.length === 0 ? (
          <p className="text-body-sm text-fg-muted">{t('detail.noStatements')}</p>
        ) : (
          <ul className="space-y-2">
            {inc.statements.map((s) => (
              <li key={s.id} className="text-body-sm">
                <span className="font-semibold text-fg">{s.party_kind}</span>{' '}
                <span className="text-fg">{s.text}</span>
              </li>
            ))}
          </ul>
        )}
        <textarea
          aria-label={t('detail.addStatement')}
          placeholder={t('detail.addStatement')}
          value={statementText}
          onChange={(e) => setStatementText(e.target.value)}
          className="min-h-[60px] w-full rounded-md border border-line-strong bg-surface-input px-3 py-2 text-body text-fg"
        />
        <Button
          variant="secondary"
          size="compact"
          disabled={!statementText.trim()}
          loading={addStatement.isPending}
          onClick={() => addStatement.mutate()}
        >
          {t('detail.send')}
        </Button>
      </Card>

      {linkedDispute && (
        <Alert tone="info">
          <Link to={`/disputes/${linkedDispute.id}`} className="underline">
            {t('detail.viewDispute')}
          </Link>
        </Alert>
      )}

      {isAdminViewer && (
        <Card className="space-y-3">
          <h2 className="text-label text-fg-secondary">{t('detail.adminActions')}</h2>
          <div className="flex flex-wrap gap-2">
            {canAct && (
              <Button
                variant="secondary"
                size="compact"
                loading={startReview.isPending}
                onClick={() => startReview.mutate()}
              >
                {t('detail.startReview')}
              </Button>
            )}
            {canAct && (
              <Button
                variant="secondary"
                size="compact"
                loading={startAmicable.isPending}
                onClick={() => startAmicable.mutate()}
              >
                {t('detail.startAmicable')}
              </Button>
            )}
            {canAct && !linkedDispute && (
              <Button
                variant="secondary"
                size="compact"
                loading={openDispute.isPending}
                onClick={() => openDispute.mutate()}
              >
                {t('detail.openDispute')}
              </Button>
            )}
          </div>

          {/* Escalate is Platform-Admin-only — hidden, not disabled, for an
              Ops Officer viewer (§17.2's explicit requirement). */}
          {isPlatformAdmin && canAct && (
            <div className="space-y-2 border-t border-line pt-3">
              <textarea
                aria-label={t('detail.escalateReason')}
                placeholder={t('detail.escalateReason')}
                value={escalateReason}
                onChange={(e) => setEscalateReason(e.target.value)}
                className="min-h-[60px] w-full rounded-md border border-line-strong bg-surface-input px-3 py-2 text-body text-fg"
              />
              <Button
                variant="destructive"
                size="compact"
                disabled={!escalateReason.trim()}
                loading={escalate.isPending}
                onClick={() => escalate.mutate()}
              >
                {t('detail.escalate')}
              </Button>
            </div>
          )}

          {(startReview.isError ||
            startAmicable.isError ||
            openDispute.isError ||
            escalate.isError) && (
            <Alert tone="danger">
              {localizeError(
                (startReview.error ?? startAmicable.error ?? openDispute.error ?? escalate.error)!,
                t,
              )}
            </Alert>
          )}
        </Card>
      )}
    </div>
  );
}
