import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { Field } from '@/components/Field';
import { Input } from '@/components/Input';
import { OtpInput } from '@/components/OtpInput';
import { PhotoCapture } from '@/components/PhotoCapture';
import { RecipientHeader } from '@/components/RecipientHeader';
import { SignaturePad } from '@/components/SignaturePad';
import { recipientApi } from '@/features/jobs/recipientApi';
import { localizeError } from '@/services/errorMessage';
import { ApiError } from '@/services/problem';

/**
 * RecipientConfirmPage — §20.2 "Confirm receipt". The recipient OTP is
 * always required (`RecipientConfirmSerializer.code` has no
 * `required=False` — a deliberate difference from the driver's delivery-
 * proof screen; see `types.ts`'s `RecipientConfirmBody` doc comment,
 * Design Phase 6 Increment 6 Decision 1). `RecipientView` deliberately
 * omits `value_band` (§20.0 disclosure table), so this screen doesn't
 * branch on band up front — it always offers an optional photo/signature,
 * and if the backend rejects with `delivery_proof_incomplete` (an
 * ELEVATED+ job needing the photo the recipient skipped), the error
 * expands that section without discarding the name/OTP already entered
 * (mirrors the existing ADR-2D-16 precedent in `DeliveryProofPage`).
 */
export function RecipientConfirmPage(): JSX.Element {
  const { token } = useParams<{ token: string }>();
  const { t } = useTranslation(['recipient', 'errors']);
  const navigate = useNavigate();

  const [partyName, setPartyName] = useState('');
  const [code, setCode] = useState('');
  const [showMoreProof, setShowMoreProof] = useState(false);
  const [signature, setSignature] = useState<File | null>(null);
  const [photo, setPhoto] = useState<File | null>(null);

  const confirm = useMutation({
    mutationFn: () =>
      recipientApi.confirm(
        token!,
        {
          code,
          party_name: partyName,
          signature: signature ?? undefined,
          photos: photo ? [photo] : undefined,
        },
        crypto.randomUUID(),
      ),
    onSuccess: () => navigate(`/r/${token}`, { replace: true }),
  });

  const proofIncomplete =
    confirm.isError && confirm.error instanceof ApiError && confirm.error.code === 'delivery_proof_incomplete';
  const expandProof = showMoreProof || proofIncomplete;

  const canSubmit = !!partyName.trim() && code.length === 6;

  return (
    <div className="min-h-full bg-surface-page">
      <RecipientHeader />
      <div className="mx-auto max-w-md space-y-4 px-4 py-6">
        <h1 className="text-h1 text-fg">{t('confirm.title')}</h1>

        <Card>
          <Field label={t('confirm.nameLabel')} required>
            {(p) => <Input {...p} value={partyName} onChange={(e) => setPartyName(e.target.value)} />}
          </Field>
        </Card>

        <Card>
          <OtpInput label={t('confirm.otpLabel')} value={code} onChange={setCode} />
        </Card>

        {proofIncomplete && <Alert tone="danger">{t('confirm.proofIncomplete')}</Alert>}

        {!expandProof && (
          <Button variant="tertiary" onClick={() => setShowMoreProof(true)}>
            {t('confirm.moreProofToggle')}
          </Button>
        )}

        {expandProof && (
          <Card className="space-y-4">
            <PhotoCapture
              value={photo}
              onChange={setPhoto}
              label={t('confirm.photoLabel')}
              retakeLabel={t('confirm.retake')}
              addedLabel={t('confirm.photoAdded')}
            />
            <SignaturePad
              value={signature}
              onChange={setSignature}
              label={t('confirm.signatureLabel')}
              clearLabel={t('confirm.clearSignature')}
            />
          </Card>
        )}

        <Button size="driver" fullWidth disabled={!canSubmit} loading={confirm.isPending} onClick={() => confirm.mutate()}>
          {t('confirm.confirm')}
        </Button>

        {confirm.isError && !proofIncomplete && <Alert tone="danger">{localizeError(confirm.error, t)}</Alert>}
      </div>
    </div>
  );
}
