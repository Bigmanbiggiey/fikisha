import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { Field } from '@/components/Field';
import { Input } from '@/components/Input';
import { OptionRows } from '@/components/OptionRow';
import { localizeError } from '@/services/errorMessage';

import { jobsApi } from './jobsApi';
import type { Job } from './types';

type Method = 'CASH' | 'MPESA';

/**
 * The sender closes a delivered job (founder 2026-10-20, PD-3 / PD-4): the
 * goods arrived and they paid the operator directly. Fikisha doesn't take or
 * move the money; this records what they paid. Only then is the job
 * completed.
 */
export function SenderCloseOffCard({ job }: { job: Job }): JSX.Element {
  const { t } = useTranslation(['jobs', 'errors']);
  const qc = useQueryClient();
  const [method, setMethod] = useState<Method>('MPESA');
  const [reference, setReference] = useState('');
  const close = useMutation({
    mutationFn: () =>
      jobsApi.closeJob(
        job.id,
        {
          payment_method: method,
          mpesa_reference: method === 'MPESA' && reference.trim() ? reference.trim() : undefined,
        },
        crypto.randomUUID(),
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['jobs'] });
    },
  });
  const refOk = /^[A-Za-z0-9]{0,20}$/.test(reference.trim());

  return (
    <Card>
      <h2 className="text-h3 text-fg">{t('jobs:closeOff.title')}</h2>
      <p className="mt-1 text-body-sm text-fg-secondary">{t('jobs:closeOff.body')}</p>
      <div className="mt-3 space-y-3">
        <OptionRows<Method>
          legend={t('jobs:closeOff.how')}
          value={method}
          onChange={setMethod}
          options={[
            { value: 'MPESA', label: t('jobs:closeOff.mpesa'), description: t('jobs:closeOff.mpesaRefHint') },
            { value: 'CASH', label: t('jobs:closeOff.cash'), description: '' },
          ]}
        />
        {method === 'MPESA' && (
          <Field label={t('jobs:closeOff.mpesaRef')} hint={t('jobs:closeOff.mpesaRefHint')}>
            {(p) => (
              <Input
                {...p}
                value={reference}
                invalid={!refOk}
                autoCapitalize="characters"
                onChange={(e) => setReference(e.target.value.toUpperCase())}
              />
            )}
          </Field>
        )}
        <Button fullWidth disabled={!refOk} loading={close.isPending} onClick={() => close.mutate()}>
          {t('jobs:closeOff.confirm')}
        </Button>
        {close.isError && <Alert tone="danger">{localizeError(close.error, t)}</Alert>}
      </div>
    </Card>
  );
}

/**
 * The operator side of close-off: waiting for the sender, with "I haven't
 * been paid" (opens a Not-paid issue, which can become a dispute), or what
 * the sender recorded once the job is completed (PD-4 / PD-5).
 */
export function OperatorPaymentCard({ job }: { job: Job }): JSX.Element | null {
  const { t } = useTranslation('jobs');
  if (job.status === 'DELIVERED') {
    return (
      <Card>
        <h2 className="text-h3 text-fg">{t('jobs:closeOff.awaitingTitle')}</h2>
        <p className="mt-1 text-body-sm text-fg-secondary">{t('jobs:closeOff.awaitingBody')}</p>
        <div className="mt-3">
          <Link
            to={`/jobs/${job.id}/report-issue?type=NON_PAYMENT`}
            className="inline-flex min-h-target items-center rounded-md border border-line-strong px-3 font-medium text-action-secondary-text"
          >
            {t('jobs:closeOff.notPaid')}
          </Link>
        </div>
      </Card>
    );
  }
  if (job.status === 'COMPLETED' && job.payment_record) {
    const p = job.payment_record;
    return (
      <Card>
        <h2 className="text-label text-fg-secondary">{t('jobs:closeOff.paidTitle')}</h2>
        <p className="mt-1 text-body text-fg">
          {p.method === 'MPESA' ? t('jobs:closeOff.paidMpesa') : t('jobs:closeOff.paidCash')}
          {p.mpesa_reference ? ` · ${t('jobs:closeOff.paidRef', { ref: p.mpesa_reference })}` : ''}
        </p>
      </Card>
    );
  }
  return null;
}
