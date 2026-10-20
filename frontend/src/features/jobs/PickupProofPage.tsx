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

import { FALLBACK_PICKUP, methodsIn, unmetGroups, type ProofMethod } from './custodyProof';
import { jobReference } from './jobHelpers';
import { jobsApi } from './jobsApi';
import { ProofChecklist } from './ProofChecklist';

/**
 * Pickup (founder assessment 2026-10-20 L-5, LD-4 / LD-5): both parties take
 * part. The sender gives the code, signs on this phone, or confirms in their
 * own app; the driver takes the photo; the driver completes. What this job
 * needs comes from the server (`custody_requirements.pickup`, by value band):
 * the checklist ticks each requirement off, and "Complete pickup" opens once
 * all are met. The operator-only fallback is gone.
 */
export function PickupProofPage(): JSX.Element {
  const { jobId } = useParams<{ jobId: string }>();
  const { t } = useTranslation(['jobs', 'errors']);
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [code, setCode] = useState('');
  const [signature, setSignature] = useState<File | null>(null);
  const [photo, setPhoto] = useState<File | null>(null);
  const [senderName, setSenderName] = useState('');

  const job = useQuery({
    queryKey: ['jobs', jobId],
    queryFn: () => jobsApi.get(jobId!),
    enabled: !!jobId,
    retry: false,
  });

  const complete = useMutation({
    mutationFn: () =>
      jobsApi.confirmPickup(
        jobId!,
        {
          code: code.length === 6 ? code : undefined,
          signature: signature ?? undefined,
          photos: photo ? [photo] : undefined,
          party_name: senderName.trim() || undefined,
        },
        crypto.randomUUID(),
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['jobs', jobId] });
      void qc.invalidateQueries({ queryKey: ['jobs'] });
      navigate(`/jobs/${jobId}/custody-confirmation`, { replace: true, state: { attested: false } });
    },
  });

  if (job.isLoading) return <PageLoader />;
  if (job.isError) {
    return <ErrorState message={localizeError(job.error, t)} error={job.error} onRetry={() => void job.refetch()} />;
  }
  const data = job.data!;
  if (data.status === 'PICKED_UP') {
    navigate(`/jobs/${jobId}/custody-confirmation`, { replace: true, state: { attested: false } });
    return <PageLoader />;
  }
  if (data.status !== 'AT_PICKUP') {
    navigate(`/jobs/${jobId}`, { replace: true });
    return <PageLoader />;
  }

  const groups = (data.custody_requirements?.pickup ?? FALLBACK_PICKUP) as ProofMethod[][];
  const offered = methodsIn(groups);
  const senderInApp = Boolean(data.custody_confirmations?.sender_in_app);
  const present = new Set<ProofMethod>();
  if (code.length === 6) present.add('OTP');
  if (signature) present.add('SIGNATURE');
  if (photo) present.add('PHOTO');
  if (senderInApp) present.add('IN_APP');
  const ready = unmetGroups(groups, present).length === 0;

  return (
    <div className="mx-auto max-w-lg space-y-4">
      <div>
        <h1 className="text-h1 text-fg">{t('jobs:pickupProof.title')}</h1>
        <p className="text-body-sm text-fg-secondary">{t('jobs:pickupProof.ref', { ref: jobReference(data.id) })}</p>
      </div>

      <ProofChecklist title={t('jobs:proof.pickupNeeds')} groups={groups} present={present} />

      {offered.has('IN_APP') && (
        <Alert tone={senderInApp ? 'success' : 'info'}>
          {senderInApp ? t('jobs:proof.senderConfirmed') : t('jobs:proof.senderCanConfirm')}
        </Alert>
      )}

      {offered.has('OTP') && (
        <Card>
          <OtpInput label={t('jobs:pickupProof.otpLabel')} value={code} onChange={setCode} />
        </Card>
      )}

      {offered.has('SIGNATURE') && (
        <Card>
          <SignaturePad
            label={t('jobs:proof.senderSigns')}
            clearLabel={t('jobs:deliveryProof.clearSignature')}
            value={signature}
            onChange={setSignature}
          />
          <div className="mt-3">
            <Field label={t('jobs:proof.senderName')}>
              {(p) => <Input {...p} value={senderName} onChange={(e) => setSenderName(e.target.value)} />}
            </Field>
          </div>
        </Card>
      )}

      {offered.has('PHOTO') && (
        <Card>
          <PhotoCapture
            value={photo}
            onChange={setPhoto}
            label={t('jobs:pickupProof.takePhoto')}
            retakeLabel={t('jobs:pickupProof.retake')}
            addedLabel={t('jobs:pickupProof.photoAdded')}
          />
        </Card>
      )}

      <Button size="driver" fullWidth disabled={!ready} loading={complete.isPending} onClick={() => complete.mutate()}>
        {t('jobs:proof.completePickup')}
      </Button>
      {complete.isError && <Alert tone="danger">{localizeError(complete.error, t)}</Alert>}
    </div>
  );
}
