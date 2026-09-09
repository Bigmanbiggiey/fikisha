import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { PageLoader } from '@/components/PageLoader';
import { StatusBadge } from '@/components/StatusBadge';
import { localizeError } from '@/services/errorMessage';

import { EVIDENCE_KINDS, verificationApi, type SubjectType } from './verificationApi';

const OK_STATES = new Set(['VERIFIED']);
const PENDING_STATES = new Set(['SUBMITTED', 'IN_REVIEW', 'INFO_REQUESTED']);

function tone(state: string): 'positive' | 'negative' | 'neutral' {
  if (OK_STATES.has(state)) return 'positive';
  if (PENDING_STATES.has(state)) return 'neutral';
  return 'negative';
}

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
    return <Alert tone="error">{localizeError(status.error, t)}</Alert>;
  }

  return (
    <Card>
      <h2 className="text-sm font-medium text-slate-700">{t('org:verification.title')}</h2>
      <ul className="mt-3 divide-y divide-slate-100 text-sm">
        {status.data.requirements.map((r) => (
          <li key={r.domain} className="py-2">
            <div className="flex items-center justify-between gap-2">
              <span className="flex items-center gap-2">
                <span className="font-medium text-slate-800">{r.domain}</span>
                <StatusBadge
                  tone={r.mandatory ? 'neutral' : 'neutral'}
                  label={r.mandatory ? t('org:verification.required') : t('org:verification.optional')}
                />
              </span>
              <span className="flex items-center gap-2">
                <StatusBadge tone={tone(r.state)} label={r.state} />
                <Button
                  variant="ghost"
                  onClick={() => setOpenDomain(openDomain === r.domain ? null : r.domain)}
                >
                  {t('org:verification.submitEvidence')}
                </Button>
              </span>
            </div>
            {openDomain === r.domain && (
              <form
                className="mt-2 flex flex-col gap-2 rounded-lg bg-slate-50 p-3 sm:flex-row sm:items-end"
                onSubmit={(e: FormEvent) => {
                  e.preventDefault();
                  if (file) submit.mutate(r.domain);
                }}
              >
                <label className="text-xs">
                  <span className="mb-1 block font-medium text-slate-600">
                    {t('org:verification.evidenceKind')}
                  </span>
                  <select
                    className="rounded-md border border-slate-300 px-2 py-1 text-sm"
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
                <label className="flex-1 text-xs">
                  <span className="mb-1 block font-medium text-slate-600">
                    {t('org:verification.file')}
                  </span>
                  <input
                    type="file"
                    accept="image/jpeg,image/png,application/pdf"
                    onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                    className="text-sm"
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
          <Alert tone="error">{error}</Alert>
        </div>
      )}
    </Card>
  );
}
