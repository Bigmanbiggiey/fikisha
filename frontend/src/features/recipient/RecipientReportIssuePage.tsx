import { useMutation } from '@tanstack/react-query';
import { useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { PhotoCapture } from '@/components/PhotoCapture';
import { RecipientHeader } from '@/components/RecipientHeader';
import { RECIPIENT_ISSUE_CATEGORIES, type RecipientIssueCategory } from '@/features/jobs/types';
import { recipientApi } from '@/features/jobs/recipientApi';
import { localizeError } from '@/services/errorMessage';

/**
 * RecipientReportIssuePage — §20.3 "Report a problem". A fixed-slot
 * `PhotoCapture` array (one empty trailing slot always available) stands in
 * for a full multi-upload component this increment — the backend accepts a
 * `photos` list (`RecipientReportIssueView`, wired alongside this frontend
 * change), but a richer drag/reorder UI is out of scope.
 */
export function RecipientReportIssuePage(): JSX.Element {
  const { token } = useParams<{ token: string }>();
  const { t } = useTranslation(['recipient', 'errors']);
  const successRef = useRef<HTMLParagraphElement>(null);

  const [category, setCategory] = useState<RecipientIssueCategory | null>(null);
  const [description, setDescription] = useState('');
  const [otherLabel, setOtherLabel] = useState('');
  const [photos, setPhotos] = useState<(File | null)[]>([null]);

  const report = useMutation({
    mutationFn: () =>
      recipientApi.reportIssue(token!, {
        category: category!,
        description: description.trim() || undefined,
        other_label: category === 'OTHER' ? otherLabel.trim() || undefined : undefined,
        photos: photos.filter((p): p is File => p !== null),
      }),
    onSuccess: () => {
      // Focus moves to the confirmation (§20.3 a11y note).
      setTimeout(() => successRef.current?.focus(), 0);
    },
  });

  function setPhotoAt(index: number, file: File | null): void {
    setPhotos((prev) => {
      const next = [...prev];
      next[index] = file;
      // Keep exactly one trailing empty slot.
      if (file && index === next.length - 1) next.push(null);
      return next;
    });
  }

  if (report.isSuccess) {
    return (
      <div className="min-h-full bg-surface-page">
        <RecipientHeader />
        <div className="mx-auto max-w-md space-y-4 px-4 py-6">
          <p ref={successRef} role="status" tabIndex={-1} className="text-h2 text-status-success-fg outline-none">
            {t('reportIssue.success')}
          </p>
          <Link to={`/r/${token}`} className="text-body-sm text-action-secondary-text underline">
            {t('reportIssue.backToDelivery')}
          </Link>
        </div>
      </div>
    );
  }

  const canSubmit = !!category && (category !== 'OTHER' || !!otherLabel.trim());

  return (
    <div className="min-h-full bg-surface-page">
      <RecipientHeader />
      <div className="mx-auto max-w-md space-y-4 px-4 py-6">
        <h1 className="text-h1 text-fg">{t('reportIssue.title')}</h1>

        <Card>
          <div role="radiogroup" aria-label={t('reportIssue.title')} className="space-y-2">
            {RECIPIENT_ISSUE_CATEGORIES.map((c) => (
              <label key={c} className="flex items-center gap-2 text-body">
                <input
                  type="radio"
                  name="category"
                  value={c}
                  checked={category === c}
                  onChange={() => setCategory(c)}
                  className="h-5 w-5"
                />
                {t(`reportIssue.category.${c}`)}
              </label>
            ))}
          </div>
        </Card>

        {category === 'OTHER' && (
          <Card>
            <textarea
              aria-label={t('reportIssue.otherLabel')}
              placeholder={t('reportIssue.otherLabel')}
              value={otherLabel}
              onChange={(e) => setOtherLabel(e.target.value)}
              className="min-h-[80px] w-full rounded-md border border-line-strong bg-surface-input px-3 py-2 text-body text-fg"
            />
          </Card>
        )}

        <Card>
          <textarea
            aria-label={t('reportIssue.description')}
            placeholder={t('reportIssue.description')}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="min-h-[80px] w-full rounded-md border border-line-strong bg-surface-input px-3 py-2 text-body text-fg"
          />
        </Card>

        <Card className="space-y-3">
          {photos.map((photo, i) => (
            <PhotoCapture
              key={i}
              value={photo}
              onChange={(f) => setPhotoAt(i, f)}
              label={i === 0 ? t('reportIssue.addPhoto') : t('reportIssue.anotherPhoto')}
              retakeLabel={t('confirm.retake')}
              addedLabel={t('confirm.photoAdded')}
            />
          ))}
        </Card>

        <Button size="driver" fullWidth disabled={!canSubmit} loading={report.isPending} onClick={() => report.mutate()}>
          {t('reportIssue.send')}
        </Button>

        {report.isError && <Alert tone="danger">{localizeError(report.error, t)}</Alert>}
      </div>
    </div>
  );
}
