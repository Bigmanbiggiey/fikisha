import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { PhotoCapture } from '@/components/PhotoCapture';
import { localizeError } from '@/services/errorMessage';

import { incidentsApi } from './incidentsApi';
import { INCIDENT_TYPES, type IncidentType } from './types';

/**
 * IncidentReportPage — §17.1 "Incident entry (any permitted actor)". Reached
 * from `JobDetailPage`'s "Report an issue" link (Business/Operator/Driver
 * viewers — a recipient's equivalent is the already-built
 * `/r/:token/report-issue`, a separate model entirely). A fixed-slot
 * `PhotoCapture` array mirrors `RecipientReportIssuePage`'s pattern, but
 * evidence here is attached with one `attachEvidence()` call per file —
 * `AttachEvidenceSerializer` takes a single `file`, not a list.
 */
export function IncidentReportPage(): JSX.Element {
  const { jobId } = useParams<{ jobId: string }>();
  const { t } = useTranslation(['incidents', 'errors']);
  const navigate = useNavigate();

  const [type, setType] = useState<IncidentType | null>(null);
  const [description, setDescription] = useState('');
  const [otherLabel, setOtherLabel] = useState('');
  const [photos, setPhotos] = useState<(File | null)[]>([null]);

  const report = useMutation({
    mutationFn: async () => {
      const incident = await incidentsApi.report(
        jobId!,
        {
          type: type!,
          description: description.trim() || undefined,
          other_label: type === 'OTHER' ? otherLabel.trim() || undefined : undefined,
        },
        crypto.randomUUID(),
      );
      for (const file of photos.filter((p): p is File => p !== null)) {
        await incidentsApi.attachEvidence(incident.id, file);
      }
      return incident;
    },
    onSuccess: (incident) => navigate(`/incidents/${incident.id}`, { replace: true }),
  });

  function setPhotoAt(index: number, file: File | null): void {
    setPhotos((prev) => {
      const next = [...prev];
      next[index] = file;
      if (file && index === next.length - 1) next.push(null);
      return next;
    });
  }

  const canSubmit = !!type && (type !== 'OTHER' || !!otherLabel.trim());

  return (
    <div className="mx-auto max-w-lg space-y-4">
      <h1 className="text-h1 text-fg">{t('report.title')}</h1>

      <Card>
        <div role="radiogroup" aria-label={t('report.category')} className="space-y-2">
          {INCIDENT_TYPES.map((c) => (
            <label key={c} className="flex items-center gap-2 text-body">
              <input
                type="radio"
                name="type"
                value={c}
                checked={type === c}
                onChange={() => setType(c)}
                className="h-5 w-5"
              />
              {t(`report.type.${c}`)}
            </label>
          ))}
        </div>
      </Card>

      {type === 'OTHER' && (
        <Card>
          <textarea
            aria-label={t('report.otherLabel')}
            placeholder={t('report.otherLabel')}
            value={otherLabel}
            onChange={(e) => setOtherLabel(e.target.value)}
            className="min-h-[80px] w-full rounded-md border border-line-strong bg-surface-input px-3 py-2 text-body text-fg"
          />
        </Card>
      )}

      <Card>
        <textarea
          aria-label={t('report.description')}
          placeholder={t('report.description')}
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
            label={i === 0 ? t('report.addEvidence') : t('report.anotherEvidence')}
            retakeLabel={t('report.retake')}
            addedLabel={t('report.evidenceAdded')}
          />
        ))}
      </Card>

      <p role="note" className="text-body-sm text-fg-secondary">
        {t('report.disclaimer')}
      </p>

      <Button fullWidth disabled={!canSubmit} loading={report.isPending} onClick={() => report.mutate()}>
        {t('report.submit')}
      </Button>

      {report.isError && <Alert tone="danger">{localizeError(report.error, t)}</Alert>}
    </div>
  );
}
