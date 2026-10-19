import { useMutation, useQueryClient, type QueryKey } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { Input } from '@/components/Input';
import { VerificationPill } from '@/components/VerificationPill';
import type { VerificationState } from '@/design/tokens';
import { useAuth } from '@/features/auth/useAuth';
import { formatDate, formatDateTime } from '@/services/datetime';
import { localizeError } from '@/services/errorMessage';

import { verificationApi, type VerificationRecord } from './verificationApi';

/**
 * One verification record with everything a reviewer acts on: its documents
 * (each fetched and logged on its own), the review actions for its state, and
 * its decision history. Used on the record page and, once per record, on the
 * applicant page (assessment 2026-10-19 part 5). The server enforces every
 * rule (reviewer permission, `reviewer_is_submitter`, state machine).
 */
export function RecordReview({
  record: r,
  refresh,
  heading,
}: {
  record: VerificationRecord;
  /** queries to refetch after an action */
  refresh: QueryKey[];
  /** the record's title (default: subject · domain) */
  heading?: string;
}): JSX.Element {
  const { t } = useTranslation(['org', 'errors']);
  const qc = useQueryClient();
  const { user } = useAuth();
  const isReviewer = Boolean(user?.is_admin);
  const [reason, setReason] = useState('');
  const [note, setNote] = useState('');
  const [error, setError] = useState<string | null>(null);

  const act = useMutation({
    mutationFn: (fn: () => Promise<unknown>) => fn(),
    onSuccess: () => {
      setError(null);
      setReason('');
      setNote('');
      for (const key of refresh) void qc.invalidateQueries({ queryKey: key });
    },
    onError: (e) => setError(localizeError(e, t)),
  });

  async function view(evidenceId: string): Promise<void> {
    try {
      const blob = await verificationApi.evidenceBlob(evidenceId);
      window.open(URL.createObjectURL(blob), '_blank', 'noopener');
    } catch (e) {
      setError(localizeError(e, t));
    }
  }

  const evidence = r.evidence ?? [];
  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-h3 text-fg">{heading ?? `${r.subject_type} · ${r.domain}`}</h3>
        <span className="flex flex-wrap gap-2">
          <VerificationPill state={r.state as VerificationState} hideDomain />
          {r.effective_state !== r.state && (
            <VerificationPill
              state={r.effective_state as VerificationState}
              hideDomain
              groupLabel={t('org:verification.now', { state: r.effective_state })}
            />
          )}
        </span>
      </div>
      {r.expires_at && (
        <p className="mt-1 text-body-sm text-fg-muted">
          {t('org:verification.expiresAt')}: {formatDate(r.expires_at)}
        </p>
      )}

      <h4 className="mt-3 text-label text-fg-secondary">{t('org:verification.evidence')}</h4>
      {evidence.length === 0 ? (
        <p className="mt-1 text-body-sm text-fg-muted">{t('org:verification.noEvidence')}</p>
      ) : (
        <ul className="mt-1 divide-y divide-line text-body-sm">
          {evidence.map((e) => (
            <li key={e.id} className="flex items-center justify-between gap-2 py-2">
              <span>
                {t(`org:verification.kind.${e.kind}`, { defaultValue: e.kind })}
                {e.superseded_at ? ` · ${t('org:verification.superseded')}` : ''}
                {e.expires_at ? ` · ${t('org:verification.expiresAt')} ${formatDate(e.expires_at)}` : ''}
              </span>
              <Button variant="ghost" onClick={() => void view(e.id)}>
                {t('org:verification.download')}
              </Button>
            </li>
          ))}
        </ul>
      )}

      {isReviewer && (
        <div className="mt-3 space-y-2">
          <h4 className="text-label text-fg-secondary">{t('org:verification.review')}</h4>
          {r.state === 'SUBMITTED' || r.state === 'INFO_REQUESTED' ? (
            <Button onClick={() => act.mutate(() => verificationApi.reviewStart(r.id))} loading={act.isPending}>
              {t('org:verification.startReview')}
            </Button>
          ) : r.state === 'IN_REVIEW' ? (
            <>
              <Input
                aria-label={t('org:verification.reason')}
                placeholder={t('org:verification.reason')}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
              <div className="flex flex-wrap gap-2">
                <Button
                  loading={act.isPending}
                  onClick={() => act.mutate(() => verificationApi.reviewApprove(r.id, reason))}
                >
                  {t('org:verification.approve')}
                </Button>
                <Button
                  variant="secondary"
                  disabled={!reason.trim()}
                  onClick={() => act.mutate(() => verificationApi.reviewReject(r.id, reason.trim()))}
                >
                  {t('org:verification.reject')}
                </Button>
              </div>
              <Input
                aria-label={t('org:verification.note')}
                placeholder={t('org:verification.note')}
                value={note}
                onChange={(e) => setNote(e.target.value)}
              />
              <Button
                variant="ghost"
                disabled={!note.trim()}
                onClick={() => act.mutate(() => verificationApi.reviewRequestInfo(r.id, note.trim()))}
              >
                {t('org:verification.requestInfo')}
              </Button>
            </>
          ) : (
            <p className="text-body-sm text-fg-muted">{t('org:verification.noAction')}</p>
          )}
          {error && <Alert tone="danger">{error}</Alert>}
        </div>
      )}

      {(r.decisions ?? []).length > 0 && (
        <>
          <h4 className="mt-3 text-label text-fg-secondary">{t('org:verification.history')}</h4>
          <ul className="mt-1 space-y-1 text-body-sm">
            {(r.decisions ?? []).map((d) => (
              <li key={d.id} className="flex flex-wrap justify-between gap-2">
                <span className="font-medium text-fg">
                  {d.action}
                  {d.actor_role ? ` · ${d.actor_role}` : ''}
                  {d.reason ? ` — ${d.reason}` : ''}
                  {d.note ? ` — ${d.note}` : ''}
                </span>
                <span className="text-fg-muted">{formatDateTime(d.created_at)}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </Card>
  );
}
