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
import { SignaturePad } from '@/components/SignaturePad';
import { localizeError } from '@/services/errorMessage';

import { jobReference } from './jobHelpers';
import { jobsApi } from './jobsApi';

type StandardMethod = 'otp' | 'signature' | 'photo';

/**
 * Delivery proof (`chain-of-custody.md` §2 `RECIPIENT_VERIFIED` row,
 * `job-state-machine.md`'s `RecipientVerificationPresent` guard) — mirrors
 * `PickupProofPage`'s structure per the plan's own instruction (no written
 * driver-side wireframe section exists for this screen; the closest spec
 * is the recipient's own §20.2 "Confirm receipt", which states the same
 * band matrix). STANDARD: recipient name + any one of {OTP, signature,
 * photo}. ELEVATED+: recipient name + OTP **and** photo, both required
 * together — not a choice.
 */
export function DeliveryProofPage(): JSX.Element {
  const { jobId } = useParams<{ jobId: string }>();
  const { t } = useTranslation(['jobs', 'errors']);
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [partyName, setPartyName] = useState('');
  const [method, setMethod] = useState<StandardMethod | null>(null);
  const [code, setCode] = useState('');
  const [signature, setSignature] = useState<File | null>(null);
  const [photo, setPhoto] = useState<File | null>(null);

  const job = useQuery({
    queryKey: ['jobs', jobId],
    queryFn: () => jobsApi.get(jobId!),
    enabled: !!jobId,
    retry: false,
  });

  const confirm = useMutation({
    mutationFn: () =>
      jobsApi.confirmDelivery(
        jobId!,
        {
          party_name: partyName,
          code: code || undefined,
          signature: signature ?? undefined,
          photos: photo ? [photo] : undefined,
        },
        crypto.randomUUID(),
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['jobs', jobId] });
      void qc.invalidateQueries({ queryKey: ['jobs'] });
      navigate(`/jobs/${jobId}`, { replace: true });
    },
  });

  if (job.isLoading) return <PageLoader />;
  if (job.isError) {
    return <ErrorState message={localizeError(job.error, t)} onRetry={() => void job.refetch()} />;
  }
  const data = job.data!;

  if (data.status !== 'AT_DESTINATION') {
    navigate(`/jobs/${jobId}`, { replace: true });
    return <PageLoader />;
  }

  const isStandard = data.value_band === 'STANDARD';
  const canSubmit = isStandard
    ? !!partyName.trim() && (!!code || !!signature || !!photo)
    : !!partyName.trim() && code.length === 6 && !!photo;

  return (
    <div className="mx-auto max-w-lg space-y-4">
      <div>
        <h1 className="text-h1 text-fg">{t('jobs:deliveryProof.title')}</h1>
        <p className="text-body-sm text-fg-secondary">{t('jobs:deliveryProof.ref', { ref: jobReference(data.id) })}</p>
      </div>

      <Alert tone="info">{t(isStandard ? 'jobs:deliveryProof.bandStandard' : 'jobs:deliveryProof.bandElevated')}</Alert>

      <Card>
        <Field label={t('jobs:deliveryProof.recipientName')} required>
          {(p) => <Input {...p} value={partyName} onChange={(e) => setPartyName(e.target.value)} />}
        </Field>
      </Card>

      {isStandard ? (
        <>
          <div className="flex flex-wrap gap-2">
            <MethodPill active={method === 'otp'} onClick={() => setMethod('otp')} label={t('jobs:deliveryProof.otpLabel')} />
            <MethodPill
              active={method === 'signature'}
              onClick={() => setMethod('signature')}
              label={t('jobs:deliveryProof.signatureLabel')}
            />
            <MethodPill
              active={method === 'photo'}
              onClick={() => setMethod('photo')}
              label={t('jobs:deliveryProof.photoLabel')}
            />
          </div>
          {method === 'otp' && (
            <Card>
              <OtpInput label={t('jobs:deliveryProof.otpLabel')} value={code} onChange={setCode} />
            </Card>
          )}
          {method === 'signature' && (
            <Card>
              <SignaturePad
                label={t('jobs:deliveryProof.signatureLabel')}
                clearLabel={t('jobs:deliveryProof.clearSignature')}
                value={signature}
                onChange={setSignature}
              />
            </Card>
          )}
          {method === 'photo' && (
            <Card>
              <PhotoCapture
                value={photo}
                onChange={setPhoto}
                label={t('jobs:deliveryProof.takePhoto')}
                retakeLabel={t('jobs:deliveryProof.retake')}
                addedLabel={t('jobs:deliveryProof.photoAdded')}
              />
            </Card>
          )}
        </>
      ) : (
        <>
          <Card>
            <h2 className="text-label text-fg-secondary">{t('jobs:deliveryProof.otpLabel')}</h2>
            <div className="mt-2">
              <OtpInput label={t('jobs:deliveryProof.otpLabel')} value={code} onChange={setCode} />
            </div>
          </Card>
          <Card>
            <h2 className="text-label text-fg-secondary">{t('jobs:deliveryProof.photoLabel')}</h2>
            <div className="mt-2">
              <PhotoCapture
                value={photo}
                onChange={setPhoto}
                label={t('jobs:deliveryProof.takePhoto')}
                retakeLabel={t('jobs:deliveryProof.retake')}
                addedLabel={t('jobs:deliveryProof.photoAdded')}
              />
            </div>
          </Card>
        </>
      )}

      <Button size="driver" fullWidth disabled={!canSubmit} loading={confirm.isPending} onClick={() => confirm.mutate()}>
        {t('jobs:deliveryProof.confirmDelivery')}
      </Button>

      {confirm.isError && <Alert tone="danger">{localizeError(confirm.error, t)}</Alert>}
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
