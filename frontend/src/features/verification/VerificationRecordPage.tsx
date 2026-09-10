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
import { VerificationPill } from '@/components/VerificationPill';
import type { VerificationState } from '@/design/tokens';
import { useAuth } from '@/features/auth/useAuth';
import { localizeError } from '@/services/errorMessage';

import { verificationApi } from './verificationApi';

export function VerificationRecordPage(): JSX.Element {
  const { recordId = '' } = useParams();
  const { t } = useTranslation(['org', 'errors']);
  const qc = useQueryClient();
  const { user } = useAuth();
  const isReviewer = Boolean(user?.is_admin);

  const record = useQuery({
    queryKey: ['verification-record', recordId],
    queryFn: () => verificationApi.getRecord(recordId),
    retry: false,
  });

  const [reason, setReason] = useState('');
  const [note, setNote] = useState('');
  const [error, setError] = useState<string | null>(null);

  const act = useMutation({
    mutationFn: (fn: () => Promise<unknown>) => fn(),
    onSuccess: () => {
      setError(null);
      void qc.invalidateQueries({ queryKey: ['verification-record', recordId] });
      void qc.invalidateQueries({ queryKey: ['verification-queue'] });
    },
    onError: (e) => setError(localizeError(e, t)),
  });

  async function download(evidenceId: string): Promise<void> {
    try {
      const blob = await verificationApi.evidenceBlob(evidenceId);
      window.open(URL.createObjectURL(blob), '_blank', 'noopener');
    } catch (e) {
      setError(localizeError(e, t));
    }
  }

  if (record.isLoading) return <PageLoader />;
  if (record.isError || !record.data) {
    return (
      <ErrorState message={localizeError(record.error, t)} onRetry={() => void record.refetch()} />
    );
  }
  const r = record.data;

  return (
    <div className="space-y-5">
      <Link to="/verification" className="text-body-sm text-action-secondary-text">
        &larr; {t('org:common.back')}
      </Link>

      <Card>
        <div className="flex items-center justify-between gap-3">
          <h1 className="text-h2 text-fg">
            {r.subject_type} · {r.domain}
          </h1>
          <span className="flex flex-wrap gap-2">
            <VerificationPill state={r.state as VerificationState} hideDomain />
            {r.effective_state !== r.state && (
              <VerificationPill
                state={r.effective_state as VerificationState}
                hideDomain
                groupLabel={`Now: ${r.effective_state}`}
              />
            )}
          </span>
        </div>
        {r.expires_at && (
          <p className="mt-1 text-body-sm text-fg-muted">
            {t('org:verification.expiresAt')}: {new Date(r.expires_at).toLocaleDateString()}
          </p>
        )}
      </Card>

      <Card>
        <h2 className="text-label text-fg-secondary">{t('org:verification.evidence')}</h2>
        <ul className="mt-2 divide-y divide-line text-body-sm">
          {(r.evidence ?? []).map((e) => (
            <li key={e.id} className="flex items-center justify-between py-2">
              <span>
                {e.kind}
                {e.superseded_at ? ' (superseded)' : ''}
                {e.expires_at ? ` · exp ${e.expires_at}` : ''}
              </span>
              <Button variant="ghost" onClick={() => void download(e.id)}>
                {t('org:verification.download')}
              </Button>
            </li>
          ))}
        </ul>
      </Card>

      {isReviewer && (
        <Card>
          <h2 className="text-label text-fg-secondary">Review</h2>
          <div className="mt-2 space-y-2">
            {r.state === 'SUBMITTED' || r.state === 'INFO_REQUESTED' ? (
              <Button
                onClick={() => act.mutate(() => verificationApi.reviewStart(r.id))}
                loading={act.isPending}
              >
                {t('org:verification.startReview')}
              </Button>
            ) : r.state === 'IN_REVIEW' ? (
              <>
                <Input
                  placeholder={t('org:verification.reason')}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
                <div className="flex flex-wrap gap-2">
                  <Button
                    onClick={() =>
                      act.mutate(() => verificationApi.reviewApprove(r.id, reason))
                    }
                  >
                    {t('org:verification.approve')}
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() =>
                      reason.trim() &&
                      act.mutate(() => verificationApi.reviewReject(r.id, reason.trim()))
                    }
                  >
                    {t('org:verification.reject')}
                  </Button>
                </div>
                <Input
                  placeholder={t('org:verification.note')}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                />
                <Button
                  variant="ghost"
                  onClick={() =>
                    note.trim() &&
                    act.mutate(() => verificationApi.reviewRequestInfo(r.id, note.trim()))
                  }
                >
                  {t('org:verification.requestInfo')}
                </Button>
              </>
            ) : (
              <p className="text-body-sm text-fg-muted">No review action available in this state.</p>
            )}
          </div>
          {error && <Alert tone="danger">{error}</Alert>}
        </Card>
      )}

      <Card>
        <h2 className="text-label text-fg-secondary">{t('org:verification.history')}</h2>
        <ul className="mt-2 space-y-1 text-body-sm">
          {(r.decisions ?? []).map((d) => (
            <li key={d.id} className="flex justify-between">
              <span className="font-medium text-fg">
                {d.action}
                {d.actor_role ? ` · ${d.actor_role}` : ''}
              </span>
              <span className="text-fg-muted">{new Date(d.created_at).toLocaleString()}</span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
