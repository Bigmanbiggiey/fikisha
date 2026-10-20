import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ErrorState } from '@/components/ErrorState';
import { PageLoader } from '@/components/PageLoader';
import { Select } from '@/components/Select';
import { Textarea } from '@/components/Textarea';
import { useAuth } from '@/features/auth/useAuth';
import { jobReference } from '@/features/jobs/jobHelpers';
import { localizeError } from '@/services/errorMessage';

import { FindingPanel } from './FindingPanel';
import { disputesApi, incidentsApi } from './incidentsApi';
import { type ClosureReason, MANUAL_CLOSURE_REASONS } from './types';

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
  const [closeReason, setCloseReason] = useState<ClosureReason | ''>('');
  const [closeNote, setCloseNote] = useState('');
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
  const closeIncident = useMutation({
    mutationFn: () =>
      incidentsApi.close(incidentId!, { reason_code: closeReason as ClosureReason, note: closeNote }),
    onSuccess: () => {
      setCloseReason('');
      setCloseNote('');
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
      <ErrorState message={localizeError(incident.error, t)} error={incident.error} onRetry={() => void incident.refetch()} />
    );
  }
  const inc = incident.data;
  const linkedDispute = disputes.data?.data.find((d) => d.incident_ids.includes(inc.id));
  const canAct = inc.status !== 'RESOLVED';
  const inOpenDispute = Boolean(linkedDispute && linkedDispute.status !== 'RESOLVED');

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

      {inc.closure && (
        <Card className="space-y-1">
          <h2 className="text-label text-fg-secondary">{t('detail.closure.title')}</h2>
          <p className="text-body text-fg">
            {t('detail.closure.reasonLine', {
              reason: t(`detail.closure.reason.${inc.closure.reason_code}`),
            })}
          </p>
          {inc.closure.note && (
            <p className="text-body-sm text-fg-secondary">
              {t('detail.closure.note')}: {inc.closure.note}
            </p>
          )}
        </Card>
      )}

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
                <Button variant="secondary" onClick={() => void downloadEvidence(e.id)}>
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
        <Textarea
          aria-label={t('detail.addStatement')}
          placeholder={t('detail.addStatement')}
          value={statementText}
          onChange={(e) => setStatementText(e.target.value)}
        />
        <Button
          variant="secondary"
          disabled={!statementText.trim()}
          loading={addStatement.isPending}
          onClick={() => addStatement.mutate()}
        >
          {t('detail.send')}
        </Button>
      </Card>

      <FindingPanel
        incident={inc}
        isStaff={isAdminViewer}
        isPlatformAdmin={isPlatformAdmin}
        onChanged={invalidate}
      />

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
                loading={startReview.isPending}
                onClick={() => startReview.mutate()}
              >
                {t('detail.startReview')}
              </Button>
            )}
            {canAct && (
              <Button
                variant="secondary"
                loading={startAmicable.isPending}
                onClick={() => startAmicable.mutate()}
              >
                {t('detail.startAmicable')}
              </Button>
            )}
            {canAct && !linkedDispute && (
              <Button
                variant="secondary"
                loading={openDispute.isPending}
                onClick={() => openDispute.mutate()}
              >
                {t('detail.openDispute')}
              </Button>
            )}
          </div>

          {canAct &&
            (inOpenDispute ? (
              <p className="border-t border-line pt-3 text-body-sm text-fg-secondary">
                {t('detail.close.inDispute')}
              </p>
            ) : (
              <div className="space-y-2 border-t border-line pt-3">
                <h3 className="text-label text-fg">{t('detail.close.title')}</h3>
                <label htmlFor="close-reason" className="block text-body-sm text-fg-secondary">
                  {t('detail.close.reason')}
                </label>
                <Select
                  id="close-reason"
                  value={closeReason}
                  onChange={(e) => setCloseReason(e.target.value as ClosureReason | '')}
                >
                  <option value="">{t('detail.close.choose')}</option>
                  {MANUAL_CLOSURE_REASONS.map((r) => (
                    <option key={r} value={r}>
                      {t(`detail.closure.reason.${r}`)}
                    </option>
                  ))}
                </Select>
                <Textarea
                  aria-label={t('detail.close.note')}
                  placeholder={t('detail.close.note')}
                  value={closeNote}
                  onChange={(e) => setCloseNote(e.target.value)}
                />
                <p className="text-caption text-fg-muted">{t('detail.close.noteHint')}</p>
                <Button
                  variant="secondary"
                  disabled={!closeReason || closeNote.trim().length < 10}
                  loading={closeIncident.isPending}
                  onClick={() => closeIncident.mutate()}
                >
                  {t('detail.close.submit')}
                </Button>
              </div>
            ))}

          {/* Escalate is Platform-Admin-only — hidden, not disabled, for an
              Ops Officer viewer (§17.2's explicit requirement). */}
          {isPlatformAdmin && canAct && (
            <div className="space-y-2 border-t border-line pt-3">
              <Textarea
                aria-label={t('detail.escalateReason')}
                placeholder={t('detail.escalateReason')}
                value={escalateReason}
                onChange={(e) => setEscalateReason(e.target.value)}
              />
              <Button
                variant="destructive"
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
            closeIncident.isError ||
            escalate.isError) && (
            <Alert tone="danger">
              {localizeError(
                (startReview.error ??
                  startAmicable.error ??
                  openDispute.error ??
                  closeIncident.error ??
                  escalate.error)!,
                t,
              )}
            </Alert>
          )}
        </Card>
      )}
    </div>
  );
}
