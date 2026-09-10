import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { PageLoader } from '@/components/PageLoader';
import { StatusBadge } from '@/components/StatusBadge';
import { VerificationPill } from '@/components/VerificationPill';
import type { VerificationState } from '@/design/tokens';
import { localizeError } from '@/services/errorMessage';

import { EVIDENCE_KINDS, verificationApi, type SubjectType } from './verificationApi';

export function VerificationPanel({
  subjectType,
  subjectId,
}: {
  subjectType: SubjectType;
  subjectId: string;
}): JSX.Element {
  const { t } = useTranslation(['org', 'errors']);
  const qc = useQueryClient();
  const key = ['verification-status', subjectType, subjectId];
  const status = useQuery({
    queryKey: key,
    queryFn: () => verificationApi.subjectStatus(subjectType, subjectId),
    retry: false,
  });

  const [openDomain, setOpenDomain] = useState<string | null>(null);
  const [kind, setKind] = useState<string>(EVIDENCE_KINDS[0]);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = useMutation({
    mutationFn: async (domain: string) => {
      if (!file) throw new Error('file required');
      const rec = await verificationApi.createRecord(subjectType, subjectId, domain);
      await verificationApi.addEvidence(rec.id, file, kind);
      return verificationApi.submit(rec.id);
    },
    onSuccess: () => {
      setOpenDomain(null);
      setFile(null);
      setError(null);
      void qc.invalidateQueries({ queryKey: key });
    },
    onError: (e) => setError(localizeError(e, t)),
  });

  if (status.isLoading) return <PageLoader />;
  if (status.isError || !status.data) {
    return <Alert tone="danger">{localizeError(status.error, t)}</Alert>;
  }

  return (
    <Card>
      <h2 className="text-label text-fg-secondary">{t('org:verification.title')}</h2>
      <ul className="mt-3 divide-y divide-line text-body-sm">
        {status.data.requirements.map((r) => (
          <li key={r.domain} className="py-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="flex items-center gap-2">
                <span className="font-semibold text-fg">{r.domain}</span>
                <StatusBadge
                  tone="neutral"
                  label={r.mandatory ? t('org:verification.required') : t('org:verification.optional')}
                />
              </span>
              <span className="flex items-center gap-2">
                <VerificationPill state={r.state as VerificationState} hideDomain />
                <Button
                  variant="ghost"
                  size="compact"
                  onClick={() => setOpenDomain(openDomain === r.domain ? null : r.domain)}
                >
                  {t('org:verification.submitEvidence')}
                </Button>
              </span>
            </div>
            {openDomain === r.domain && (
              <form
                className="mt-2 flex flex-col gap-2 rounded-md bg-surface-sunken p-3 sm:flex-row sm:items-end"
                onSubmit={(e: FormEvent) => {
                  e.preventDefault();
                  if (file) submit.mutate(r.domain);
                }}
              >
                <label className="text-caption">
                  <span className="mb-1 block font-medium text-fg-secondary">
                    {t('org:verification.evidenceKind')}
                  </span>
                  <select
                    className="min-h-target rounded-md border border-line-strong bg-surface-input px-2 text-body-sm text-fg"
                    value={kind}
                    onChange={(e) => setKind(e.target.value)}
                  >
                    {EVIDENCE_KINDS.map((k) => (
                      <option key={k} value={k}>
                        {k}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="flex-1 text-caption">
                  <span className="mb-1 block font-medium text-fg-secondary">
                    {t('org:verification.file')}
                  </span>
                  <input
                    type="file"
                    accept="image/jpeg,image/png,application/pdf"
                    onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                    className="text-body-sm text-fg-secondary file:mr-2 file:min-h-target file:rounded-md file:border file:border-line-strong file:bg-surface-card file:px-3 file:text-body-sm"
                  />
                </label>
                <Button type="submit" loading={submit.isPending} disabled={!file}>
                  {t('org:common.add')}
                </Button>
              </form>
            )}
          </li>
        ))}
      </ul>
      {error && (
        <div className="mt-2">
          <Alert tone="danger">{error}</Alert>
        </div>
      )}
    </Card>
  );
}
