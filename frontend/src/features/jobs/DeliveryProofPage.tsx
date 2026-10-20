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

import { FALLBACK_DELIVERY, methodsIn, unmetGroups, type ProofMethod } from './custodyProof';
import { jobReference } from './jobHelpers';
import { jobsApi } from './jobsApi';
import { ProofChecklist } from './ProofChecklist';

/**
 * Delivery (founder assessment 2026-10-20 L-5, LD-4 / LD-5): the recipient's
 * name, plus what this job's band needs (`custody_requirements.delivery`):
 * by default STANDARD the code or a signature; ELEVATED the code and the
 * driver's photo; HIGH and VERY_HIGH all three. A code or signature the
 * recipient already gave through their link counts. The driver completes.
 */
export function DeliveryProofPage(): JSX.Element {
  const { jobId } = useParams<{ jobId: string }>();
  const { t } = useTranslation(['jobs', 'errors']);
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [partyName, setPartyName] = useState('');
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
          code: code.length === 6 ? code : undefined,
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
    return <ErrorState message={localizeError(job.error, t)} error={job.error} onRetry={() => void job.refetch()} />;
  }
  const data = job.data!;
  if (data.status !== 'AT_DESTINATION') {
    navigate(`/jobs/${jobId}`, { replace: true });
    return <PageLoader />;
  }

  const groups = (data.custody_requirements?.delivery ?? FALLBACK_DELIVERY) as ProofMethod[][];
  const offered = methodsIn(groups);
  const viaLink = data.custody_confirmations;
  const present = new Set<ProofMethod>();
  if (code.length === 6 || viaLink?.recipient_code) present.add('OTP');
  if (signature || viaLink?.recipient_signature) present.add('SIGNATURE');
  if (photo) present.add('PHOTO');
  const ready = partyName.trim().length > 0 && unmetGroups(groups, present).length === 0;

  return (
    <div className="mx-auto max-w-lg space-y-4">
      <div>
        <h1 className="text-h1 text-fg">{t('jobs:deliveryProof.title')}</h1>
        <p className="text-body-sm text-fg-secondary">{t('jobs:deliveryProof.ref', { ref: jobReference(data.id) })}</p>
      </div>

      <ProofChecklist title={t('jobs:proof.deliveryNeeds')} groups={groups} present={present} />
      {viaLink?.recipient_code && <Alert tone="success">{t('jobs:proof.recipientConfirmed')}</Alert>}

      <Card>
        <Field label={t('jobs:deliveryProof.recipientName')} required>
          {(p) => <Input {...p} value={partyName} onChange={(e) => setPartyName(e.target.value)} />}
        </Field>
      </Card>

      {offered.has('OTP') && !viaLink?.recipient_code && (
        <Card>
          <OtpInput label={t('jobs:deliveryProof.otpLabel')} value={code} onChange={setCode} />
        </Card>
      )}

      {offered.has('SIGNATURE') && !viaLink?.recipient_signature && (
        <Card>
          <SignaturePad
            label={t('jobs:deliveryProof.signatureLabel')}
            clearLabel={t('jobs:deliveryProof.clearSignature')}
            value={signature}
            onChange={setSignature}
          />
        </Card>
      )}

      {offered.has('PHOTO') && (
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

      <Button size="driver" fullWidth disabled={!ready} loading={confirm.isPending} onClick={() => confirm.mutate()}>
        {t('jobs:deliveryProof.confirmDelivery')}
      </Button>
      {confirm.isError && <Alert tone="danger">{localizeError(confirm.error, t)}</Alert>}
    </div>
  );
}
