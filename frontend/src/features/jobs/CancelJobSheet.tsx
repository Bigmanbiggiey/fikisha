import { useMutation } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Modal } from '@/components/Modal';
import { localizeError } from '@/services/errorMessage';

import { BUSINESS_CANCEL_REASONS, cancelConsequence, jobReference } from './jobHelpers';
import { jobsApi } from './jobsApi';
import type { CancellationReason, JobStatus, JobTransitionResult } from './types';

const textareaClass =
  'min-h-[72px] w-full rounded-md border border-line-strong bg-surface-input px-3 py-2 text-body text-fg';

/**
 * Business cancel (Design Phase 7 P-02, F-02; P3 §6.4 "Cancel (with reason;
 * consequence screen if a late-cancel — §23)"). Replaces the old one-tap
 * cancel that always sent `BUSINESS_CHANGED_MIND`. The reason is required,
 * the note optional, and the consequence line shows *before* confirming.
 * One idempotency key per opening of the sheet.
 */
export function CancelJobSheet({
  open,
  onClose,
  jobId,
  status,
  onCancelled,
}: {
  open: boolean;
  onClose: () => void;
  jobId: string;
  status: JobStatus;
  onCancelled: (result: JobTransitionResult) => void;
}): JSX.Element {
  const { t } = useTranslation(['jobs', 'errors']);
  const [reason, setReason] = useState<CancellationReason | null>(null);
  const [note, setNote] = useState('');
  const [key, setKey] = useState('');

  const cancel = useMutation({
    mutationFn: () =>
      jobsApi.cancel(jobId, { reason_code: reason!, reason_text: note.trim() || undefined }, key),
    onSuccess: (result) => onCancelled(result),
  });
  const resetCancel = cancel.reset;

  // Each opening is a fresh attempt: clear the form, the key and any error
  // left from a previous, failed attempt.
  useEffect(() => {
    if (open) {
      setReason(null);
      setNote('');
      setKey(crypto.randomUUID());
      resetCancel();
    }
  }, [open, resetCancel]);

  const consequence = cancelConsequence(status);

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={t('jobs:cancel.title', { ref: jobReference(jobId) })}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t('jobs:cancel.keep')}
          </Button>
          <Button variant="destructive" disabled={!reason} loading={cancel.isPending} onClick={() => cancel.mutate()}>
            {t('jobs:cancel.confirm')}
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        <fieldset className="space-y-2">
          <legend className="text-label text-fg-secondary">{t('jobs:cancel.why')}</legend>
          {BUSINESS_CANCEL_REASONS.map((code) => (
            <label
              key={code}
              className="flex min-h-target cursor-pointer items-center gap-3 rounded-md border border-line-strong bg-surface-input px-3 py-2 text-body text-fg has-[:checked]:border-action-primary has-[:checked]:bg-surface-brand-tint"
            >
              <input
                type="radio"
                name="cancel-reason"
                value={code}
                checked={reason === code}
                onChange={() => setReason(code)}
              />
              {t(`jobs:cancel.reason.${code}`)}
            </label>
          ))}
        </fieldset>

        <label htmlFor="cancel-note" className="block text-label text-fg-secondary">
          {t('jobs:cancel.note')}
        </label>
        <textarea
          id="cancel-note"
          value={note}
          maxLength={2000}
          onChange={(e) => setNote(e.target.value)}
          className={textareaClass}
        />

        <Alert tone={consequence === 'none' ? 'info' : 'warning'}>{t(`jobs:cancel.consequence.${consequence}`)}</Alert>
        {cancel.isError && <Alert tone="danger">{localizeError(cancel.error, t)}</Alert>}
      </div>
    </Modal>
  );
}
