import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Input } from '@/components/Input';
import { Modal } from '@/components/Modal';
import { Textarea } from '@/components/Textarea';
import { ApiError } from '@/services/problem';
import { localizeError } from '@/services/errorMessage';

export const REASON_MIN_LENGTH = 10;


/**
 * The Platform-Admin-only action shell (P3 §19.2), shared by every gated
 * action: review → reason (required) → [fresh MFA] → a confirm step that
 * restates the action and its target → apply. The server writes the audit
 * row in the same transaction.
 *
 * The MFA step-up isn't built yet (Increment 9 D-1, deferred), so the
 * server refuses these actions with `step_up_required`. The dialog says so
 * up front and again if it happens; nothing here pretends otherwise.
 */
export function AdminActionDialog({
  open,
  onClose,
  title,
  restatement,
  confirmLabel,
  destructive = true,
  allowDuration = false,
  pending,
  error,
  onConfirm,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  /** "Suspend operator A. Otieno" — shown on the confirm step */
  restatement: string;
  confirmLabel: string;
  destructive?: boolean;
  allowDuration?: boolean;
  pending: boolean;
  error: unknown;
  onConfirm: (input: { reason: string; durationDays: number | null }) => void;
}): JSX.Element {
  const { t } = useTranslation(['admin', 'errors']);
  const [step, setStep] = useState<'reason' | 'confirm'>('reason');
  const [reason, setReason] = useState('');
  const [duration, setDuration] = useState('');

  const trimmed = reason.trim();
  const durationDays = duration.trim() ? Number(duration) : null;
  const durationValid = durationDays === null || (Number.isInteger(durationDays) && durationDays >= 1 && durationDays <= 365);
  const ready = trimmed.length >= REASON_MIN_LENGTH && durationValid;
  const stepUpMissing = error instanceof ApiError && error.code === 'step_up_required';

  function close(): void {
    setStep('reason');
    setReason('');
    setDuration('');
    onClose();
  }

  return (
    <Modal
      open={open}
      onClose={close}
      title={title}
      footer={
        step === 'reason' ? (
          <>
            <Button variant="secondary" onClick={close}>
              {t('admin:action.cancel')}
            </Button>
            <Button disabled={!ready} onClick={() => setStep('confirm')}>
              {t('admin:action.continue')}
            </Button>
          </>
        ) : (
          <>
            <Button variant="secondary" onClick={() => setStep('reason')}>
              {t('admin:action.back')}
            </Button>
            <Button
              variant={destructive ? 'destructive' : 'primary'}
              loading={pending}
              onClick={() => onConfirm({ reason: trimmed, durationDays })}
            >
              {confirmLabel}
            </Button>
          </>
        )
      }
    >
      <div className="space-y-3">
        <Alert tone="info">{t('admin:action.mfaNotice')}</Alert>
        {step === 'reason' ? (
          <>
            <label htmlFor="admin-action-reason" className="block text-label text-fg-secondary">
              {t('admin:action.reason')}
            </label>
            <Textarea
              id="admin-action-reason"
              aria-describedby="admin-action-reason-hint"
              value={reason}
              maxLength={2000}
              onChange={(e) => setReason(e.target.value)}
            />
            <p id="admin-action-reason-hint" className="text-body-sm text-fg-muted">
              {t('admin:action.reasonHint', { count: REASON_MIN_LENGTH })}
            </p>
            {allowDuration && (
              <div className="space-y-1">
                <label htmlFor="admin-action-duration" className="block text-label text-fg-secondary">
                  {t('admin:action.duration')}
                </label>
                <Input
                  id="admin-action-duration"
                  inputMode="numeric"
                  value={duration}
                  invalid={!durationValid}
                  aria-describedby="admin-action-duration-hint"
                  onChange={(e) => setDuration(e.target.value)}
                />
                <p id="admin-action-duration-hint" className="text-body-sm text-fg-muted">
                  {t('admin:action.durationHint')}
                </p>
              </div>
            )}
          </>
        ) : (
          <>
            <p className="text-body font-semibold text-fg">{restatement}</p>
            <p className="text-body-sm text-fg-secondary">
              {t('admin:action.reasonLabel')} {trimmed}
            </p>
            {durationDays !== null && (
              <p className="text-body-sm text-fg-secondary">{t('admin:action.durationLabel', { count: durationDays })}</p>
            )}
            <p className="text-body-sm text-fg-muted">{t('admin:action.audited')}</p>
          </>
        )}
        {error != null && (
          <Alert tone={stepUpMissing ? 'warning' : 'danger'}>
            {stepUpMissing ? t('admin:action.stepUpMissing') : localizeError(error, t)}
          </Alert>
        )}
      </div>
    </Modal>
  );
}
