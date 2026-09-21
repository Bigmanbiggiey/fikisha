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
import { Modal } from '@/components/Modal';
import { PageLoader } from '@/components/PageLoader';
import { negotiationApi } from '@/features/negotiation/negotiationApi';
import { localizeError } from '@/services/errorMessage';
import { useWorkspaces } from '@/shell/useWorkspaces';

import { jobReference } from './jobHelpers';
import { jobsApi } from './jobsApi';
import { formatKes, parseKesToMinorUnits } from './money';

type Respond = 'accept' | 'counter' | null;

/**
 * Job Opportunity (`design-phase-3-wireframes.md` §7.3) — an operator
 * evaluating a job they haven't negotiated on yet. Reached only from Work
 * discovery; `GET /jobs/:jobId/opportunity` is used instead of the ordinary
 * job-detail read, since `job.read` authz requires already being a
 * negotiation party (which the operator isn't yet).
 *
 * "Accept the posted price" is two calls, not one: `negotiation.propose()`
 * is what opens the thread (there's no thread to `accept()` against yet),
 * so accepting on first contact still needs the operator's own PROPOSE
 * entry recorded before their ACCEPT can reference it. This does not, by
 * itself, confirm the job — the business must independently accept too
 * (`mutual_acceptance` requires an ACCEPT from both sides); the UI is
 * explicit that this sends an offer, not a done deal.
 *
 * "Decline" is a pure client-side dismissal — the operator was never a
 * negotiation party, so there is nothing to persist.
 */
export function JobOpportunityPage(): JSX.Element {
  const { jobId } = useParams<{ jobId: string }>();
  const { t } = useTranslation(['jobs', 'errors']);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { workspaces } = useWorkspaces();
  const operatorId = workspaces.find((w) => w.kind === 'OPERATOR')?.id ?? null;

  const [sheetOpen, setSheetOpen] = useState(false);
  const [respondMode, setRespondMode] = useState<Respond>(null);
  const [counterAmount, setCounterAmount] = useState('');

  const opportunity = useQuery({
    queryKey: ['jobs', jobId, 'opportunity'],
    queryFn: () => jobsApi.opportunity(jobId!),
    enabled: !!jobId,
    retry: false,
  });

  const acceptPrice = useMutation({
    mutationFn: async (amountKes: number) => {
      const thread = await negotiationApi.propose(
        jobId!,
        { operator_id: operatorId!, amount_kes: amountKes },
        crypto.randomUUID(),
      );
      return negotiationApi.accept(thread.thread_id, { amount_kes: amountKes }, crypto.randomUUID());
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['jobs'] });
      navigate(`/jobs/${jobId}`, { replace: true });
    },
  });

  const counterOffer = useMutation({
    mutationFn: (amountKes: number) =>
      negotiationApi.propose(jobId!, { operator_id: operatorId!, amount_kes: amountKes }, crypto.randomUUID()),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['jobs'] });
      navigate(`/jobs/${jobId}`, { replace: true });
    },
  });

  if (opportunity.isLoading) return <PageLoader />;
  if (opportunity.isError) {
    return (
      <ErrorState message={localizeError(opportunity.error, t)} onRetry={() => void opportunity.refetch()} />
    );
  }
  const data = opportunity.data!;
  const busy = acceptPrice.isPending || counterOffer.isPending;

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <div>
        <h1 className="text-h1 text-fg">{t('jobs:opportunity.title')}</h1>
        <p className="text-body-sm text-fg-secondary">{t('jobs:opportunity.ref', { ref: jobReference(data.id) })}</p>
      </div>

      <Card>
        <h2 className="text-label text-fg-secondary">{t('jobs:detail.route')}</h2>
        <dl className="mt-2 space-y-1 text-body">
          <div className="flex justify-between gap-3">
            <dt className="text-fg-muted">{t('jobs:detail.pickup')}</dt>
            <dd className="text-fg">{data.pickup_location?.address_text || '—'}</dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-fg-muted">{t('jobs:detail.destination')}</dt>
            <dd className="text-fg">{data.destination_location?.address_text || '—'}</dd>
          </div>
        </dl>
      </Card>

      <Card>
        <h2 className="text-label text-fg-secondary">{t('jobs:detail.cargo')}</h2>
        <p className="mt-2 text-body text-fg">{data.cargo?.description || '—'}</p>
        <p className="mt-1 text-body-sm text-fg-secondary">
          {t('jobs:opportunity.declaredValue', {
            value: data.cargo ? formatKes(data.cargo.declared_value_kes) : '—',
            band: t(`jobs:opportunity.band.${data.value_band}`),
          })}
        </p>
      </Card>

      <Card>
        <h2 className="text-label text-fg-secondary">{t('jobs:opportunity.yourEligibility')}</h2>
        {data.eligibility.eligible ? (
          <p className="mt-2 text-body text-status-success-fg">{t('jobs:opportunity.eligibleYes')}</p>
        ) : (
          <div className="mt-2">
            {data.eligibility.reasons.map((reason) => (
              <p key={reason} className="text-body text-status-danger-fg">
                {reason}
              </p>
            ))}
          </div>
        )}
      </Card>

      <Card>
        <h2 className="text-label text-fg-secondary">{t('jobs:detail.price')}</h2>
        <p className="mt-2 fk-numeric text-h3 text-fg">
          {data.proposed_price_kes != null ? formatKes(data.proposed_price_kes) : '—'}
        </p>
      </Card>

      <Button
        fullWidth
        disabled={!data.eligibility.eligible}
        onClick={() => {
          setRespondMode(null);
          setSheetOpen(true);
        }}
      >
        {t('jobs:opportunity.respond')}
      </Button>

      <Modal
        open={sheetOpen}
        onClose={() => setSheetOpen(false)}
        title={t('jobs:opportunity.respond')}
        footer={
          respondMode === 'counter' ? (
            <>
              <Button variant="secondary" onClick={() => setRespondMode(null)} disabled={busy}>
                {t('jobs:create.back')}
              </Button>
              <Button
                loading={counterOffer.isPending}
                disabled={!counterAmount}
                onClick={() => {
                  const minor = parseKesToMinorUnits(counterAmount);
                  if (minor != null) counterOffer.mutate(minor);
                }}
              >
                {t('jobs:opportunity.sendCounter')}
              </Button>
            </>
          ) : undefined
        }
      >
        {respondMode === null && (
          <div className="space-y-2">
            <Button
              fullWidth
              loading={acceptPrice.isPending}
              onClick={() => data.proposed_price_kes != null && acceptPrice.mutate(data.proposed_price_kes)}
            >
              {t('jobs:opportunity.acceptPrice', {
                price: data.proposed_price_kes != null ? formatKes(data.proposed_price_kes) : '',
              })}
            </Button>
            <Button fullWidth variant="secondary" onClick={() => setRespondMode('counter')}>
              {t('jobs:opportunity.counter')}
            </Button>
            <Button fullWidth variant="ghost" onClick={() => navigate('/work', { replace: true })}>
              {t('jobs:opportunity.decline')}
            </Button>
          </div>
        )}
        {respondMode === 'counter' && (
          <Field label={t('jobs:opportunity.counterAmount')}>
            {(p) => (
              <Input
                {...p}
                type="text"
                inputMode="numeric"
                value={counterAmount}
                onChange={(e) => setCounterAmount(e.target.value)}
                placeholder="0"
              />
            )}
          </Field>
        )}
        {(acceptPrice.isError || counterOffer.isError) && (
          <div className="mt-3">
            <Alert tone="danger">{localizeError((acceptPrice.error ?? counterOffer.error)!, t)}</Alert>
          </div>
        )}
      </Modal>
    </div>
  );
}
