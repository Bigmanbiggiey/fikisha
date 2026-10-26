import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { Select } from '@/components/Select';
import { Textarea } from '@/components/Textarea';
import { Icon } from '@/design/Icon';
import { formatDateTime } from '@/services/datetime';
import { localizeError } from '@/services/errorMessage';

import { disputesApi } from './incidentsApi';
import { AGREEMENT_METHODS, type AgreementMethod, type Dispute } from './types';

const MIN_REASON = 10;

/**
 * Resume a disputed job to the state it was in before the dispute (trust
 * plan Part B, ADR-2D-54). Staff see the checklist; only a Platform Admin
 * resumes, recording how each party agreed (with a fresh step-up, which
 * the request asks for on its own). No replacement driver or vehicle; the
 * pending pickup or delivery is confirmed again afterwards.
 */
export function ResumeCard({ dispute, canResume }: { dispute: Dispute; canResume: boolean }): JSX.Element | null {
  const { t } = useTranslation(['incidents', 'jobs', 'errors']);
  const qc = useQueryClient();
  const [sender, setSender] = useState<AgreementMethod | ''>('');
  const [operator, setOperator] = useState<AgreementMethod | ''>('');
  const [reason, setReason] = useState('');
  const checks = useQuery({
    queryKey: ['disputes', dispute.id, 'resume'],
    queryFn: () => disputesApi.resumeChecks(dispute.id),
    retry: false,
  });
  const resume = useMutation({
    mutationFn: () =>
      disputesApi.resume(
        dispute.id,
        { sender_method: sender as AgreementMethod, operator_method: operator as AgreementMethod, reason },
        crypto.randomUUID(),
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['disputes-detail', dispute.id] });
      void qc.invalidateQueries({ queryKey: ['jobs', dispute.job_id] });
      void qc.invalidateQueries({ queryKey: ['disputes', dispute.job_id] });
    },
  });
  if (!checks.data) return null;
  const c = checks.data;
  const status = t(`jobs:status.${c.target_status}`);
  const ready = c.ok && sender !== '' && operator !== '' && reason.trim().length >= MIN_REASON;

  return (
    <Card className="space-y-3">
      <h2 className="text-label text-fg-secondary">{t('dispute.resume.title', { status })}</h2>
      <p className="text-body-sm text-fg-secondary">{t('dispute.resume.explain')}</p>
      <ul className="space-y-1">
        {c.checks.map((row) => (
          <li key={row.key} className="flex items-start gap-2 text-body-sm">
            <span className={row.ok ? 'text-status-success-fg' : 'text-status-danger-fg'}>
              <Icon name={row.ok ? 'check' : 'circle'} />
            </span>
            <span className="text-fg">
              {t(`dispute.resume.check.${row.key}`, {
                when: row.key === 'within_window' ? formatDateTime(c.window_ends_at) : '',
              })}
              {!row.ok && row.key === 'assignment_eligible' && row.detail && (
                <span className="block text-fg-muted">{row.detail}</span>
              )}
              <span className="sr-only"> · {t(row.ok ? 'dispute.resume.met' : 'dispute.resume.notMet')}</span>
            </span>
          </li>
        ))}
      </ul>

      {canResume ? (
        <div className="space-y-2 border-t border-line pt-3">
          <label htmlFor="resume-sender" className="block text-body-sm text-fg-secondary">
            {t('dispute.resume.senderAgreed')}
          </label>
          <Select id="resume-sender" value={sender} onChange={(e) => setSender(e.target.value as AgreementMethod | '')}>
            <option value="">{t('dispute.resume.chooseMethod')}</option>
            {AGREEMENT_METHODS.map((m) => (
              <option key={m} value={m}>
                {t(`dispute.resume.method.${m}`)}
              </option>
            ))}
          </Select>
          <label htmlFor="resume-operator" className="block text-body-sm text-fg-secondary">
            {t('dispute.resume.operatorAgreed')}
          </label>
          <Select id="resume-operator" value={operator} onChange={(e) => setOperator(e.target.value as AgreementMethod | '')}>
            <option value="">{t('dispute.resume.chooseMethod')}</option>
            {AGREEMENT_METHODS.map((m) => (
              <option key={m} value={m}>
                {t(`dispute.resume.method.${m}`)}
              </option>
            ))}
          </Select>
          <Textarea
            aria-label={t('dispute.resume.reason')}
            placeholder={t('dispute.resume.reason')}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
          <p className="text-caption text-fg-muted">{t('dispute.resume.afterwards')}</p>
          <Button fullWidth disabled={!ready} loading={resume.isPending} onClick={() => resume.mutate()}>
            {t('dispute.resume.action', { status })}
          </Button>
          {resume.isError && <Alert tone="danger">{localizeError(resume.error, t)}</Alert>}
        </div>
      ) : (
        <p className="text-body-sm text-fg-muted">{t('dispute.resume.platformAdminOnly')}</p>
      )}
    </Card>
  );
}
