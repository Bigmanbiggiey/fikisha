import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ErrorState } from '@/components/ErrorState';
import { Field } from '@/components/Field';
import { Input } from '@/components/Input';
import { OtpInput } from '@/components/OtpInput';
import { PageLoader } from '@/components/PageLoader';
import { PhotoCapture } from '@/components/PhotoCapture';
import { localizeError } from '@/services/errorMessage';

import { jobReference } from './jobHelpers';
import { jobsApi } from './jobsApi';

type Method = 'otp' | 'business' | 'attested';

/**
 * Pickup proof (`chain-of-custody.md` §4, `design-phase-3-wireframes.md`
 * §11.1–11.3) — the exact band matrix, implemented exactly, no invented
 * fallback: STANDARD gets a third "operator-attested" segment (photo +
 * contact name, caps the job at STANDARD, marked unverified); ELEVATED+
 * gets only the two verified paths, with no fallback rendered at all.
 *
 * "Sender confirms in app" isn't something the driver submits — it's the
 * Business's own action (`PickupConfirmPage.tsx` §6.6, same transition,
 * same lifecycle writer) — this screen shows it as a passive state with a
 * manual refresh, and auto-advances once the job moves off `AT_PICKUP`.
 */
export function PickupProofPage(): JSX.Element {
  const { jobId } = useParams<{ jobId: string }>();
  const { t } = useTranslation(['jobs', 'errors']);
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [method, setMethod] = useState<Method | null>(null);
  const [code, setCode] = useState('');
  const [contactName, setContactName] = useState('');
  const [photo, setPhoto] = useState<File | null>(null);

  const job = useQuery({
    queryKey: ['jobs', jobId],
    queryFn: () => jobsApi.get(jobId!),
    enabled: !!jobId,
    retry: false,
  });

  function onProofSuccess(attested: boolean): void {
    void qc.invalidateQueries({ queryKey: ['jobs', jobId] });
    void qc.invalidateQueries({ queryKey: ['jobs'] });
    // The Job DTO carries no field for which proof method was used (a
    // documented gap — flagged for a future increment to close properly).
    // Passed via navigation state since it's known here and nowhere else;
    // a direct reload of the confirmation screen loses it and falls back
    // to the "verified" default (see CustodyConfirmationPage).
    navigate(`/jobs/${jobId}/custody-confirmation`, { replace: true, state: { attested } });
  }

  const confirmOtp = useMutation({
    mutationFn: () => jobsApi.confirmPickupOtp(jobId!, { code }, crypto.randomUUID()),
    onSuccess: () => onProofSuccess(false),
  });
  const confirmAttested = useMutation({
    mutationFn: () => {
      if (!photo) throw new Error('photo required');
      return jobsApi.confirmPickupAttested(
        jobId!,
        { pickup_contact_name: contactName, photo },
        crypto.randomUUID(),
      );
    },
    onSuccess: () => onProofSuccess(true),
  });

  if (job.isLoading) return <PageLoader />;
  if (job.isError) {
    return <ErrorState message={localizeError(job.error, t)} onRetry={() => void job.refetch()} />;
  }
  const data = job.data!;

  if (data.status === 'PICKED_UP') {
    // The business confirmed pickup in-app while this screen was open
    // (§9.3: one lifecycle, no second transition mechanism) — same
    // destination as this screen's own OTP/attested success path.
    navigate(`/jobs/${jobId}/custody-confirmation`, { replace: true, state: { attested: false } });
    return <PageLoader />;
  }
  if (data.status !== 'AT_PICKUP') {
    // Moved on some other way, or stale — Current Job home has the truth.
    navigate(`/jobs/${jobId}`, { replace: true });
    return <PageLoader />;
  }

  const isStandard = data.value_band === 'STANDARD';

  return (
    <div className="mx-auto max-w-lg space-y-4">
      <div>
        <h1 className="text-h1 text-fg">{t('jobs:pickupProof.title')}</h1>
        <p className="text-body-sm text-fg-secondary">{t('jobs:pickupProof.ref', { ref: jobReference(data.id) })}</p>
      </div>

      <Alert tone="info">{t(isStandard ? 'jobs:pickupProof.bandStandard' : 'jobs:pickupProof.bandElevated')}</Alert>

      <div className="flex flex-wrap gap-2">
        <MethodPill active={method === 'otp'} onClick={() => setMethod('otp')} label={t('jobs:pickupProof.enterCode')} />
        <MethodPill
          active={method === 'business'}
          onClick={() => setMethod('business')}
          label={t('jobs:pickupProof.senderConfirms')}
        />
        {isStandard && (
          <MethodPill
            active={method === 'attested'}
            onClick={() => setMethod('attested')}
            label={t('jobs:pickupProof.codeNotWorking')}
          />
        )}
      </div>

      {method === 'otp' && (
        <Card>
          <OtpInput
            label={t('jobs:pickupProof.otpLabel')}
            value={code}
            onChange={setCode}
            error={confirmOtp.isError ? localizeError(confirmOtp.error, t) : undefined}
          />
          <div className="mt-4">
            <Button
              size="driver"
              fullWidth
              disabled={code.length < 6}
              loading={confirmOtp.isPending}
              onClick={() => confirmOtp.mutate()}
            >
              {t('jobs:pickupProof.confirmHandover')}
            </Button>
          </div>
          {!isStandard && confirmOtp.isError && (
            <p className="mt-3 text-body-sm text-status-danger-fg">{t('jobs:pickupProof.blockingExplainer')}</p>
          )}
        </Card>
      )}

      {method === 'business' && (
        <Card>
          <p className="text-body text-fg-secondary">{t('jobs:pickupProof.waitingForSender')}</p>
          <div className="mt-3">
            <Button variant="secondary" onClick={() => void job.refetch()} loading={job.isFetching}>
              {t('jobs:pickupProof.checkStatus')}
            </Button>
          </div>
        </Card>
      )}

      {method === 'attested' && isStandard && (
        <Card>
          <Alert tone="warning">{t('jobs:pickupProof.attestedWarning')}</Alert>
          <div className="mt-3">
            <Field label={t('jobs:pickupProof.contactName')} required>
              {(p) => <Input {...p} value={contactName} onChange={(e) => setContactName(e.target.value)} />}
            </Field>
          </div>
          <div className="mt-3">
            <PhotoCapture
              value={photo}
              onChange={setPhoto}
              label={t('jobs:pickupProof.takePhoto')}
              retakeLabel={t('jobs:pickupProof.retake')}
              addedLabel={t('jobs:pickupProof.photoAdded')}
            />
          </div>
          <div className="mt-4">
            <Button
              size="driver"
              fullWidth
              disabled={!contactName.trim() || !photo}
              loading={confirmAttested.isPending}
              onClick={() => confirmAttested.mutate()}
            >
              {t('jobs:pickupProof.confirmHandover')}
            </Button>
          </div>
          {confirmAttested.isError && (
            <Alert tone="danger">{localizeError(confirmAttested.error, t)}</Alert>
          )}
        </Card>
      )}
    </div>
  );
}

function MethodPill({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }): JSX.Element {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`rounded-full border px-3 py-2 text-body-sm ${
        active ? 'border-action-primary bg-surface-brand-tint text-fg' : 'border-line text-fg-secondary'
      }`}
    >
      {label}
    </button>
  );
}
