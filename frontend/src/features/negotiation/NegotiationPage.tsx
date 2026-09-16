import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { Field } from '@/components/Field';
import { Input } from '@/components/Input';
import { NegotiationThread as NegotiationThreadList } from '@/components/NegotiationThread';
import { PageLoader } from '@/components/PageLoader';
import { formatKes, parseKesToMinorUnits } from '@/features/jobs/money';
import { jobsApi } from '@/features/jobs/jobsApi';
import { localizeError } from '@/services/errorMessage';
import { ApiError } from '@/services/problem';

import { negotiationApi } from './negotiationApi';
import type { NegotiationThread } from './types';

/**
 * Business-side negotiation thread (`design-phase-3-wireframes.md` §8.1),
 * reachable from Job Detail's "Review offers" once a job is `NEGOTIATING`.
 * Shared with Operator (Increment 4) via `NegotiationThread`/`OfferCard`
 * (`src/components/`); everything below this component's own composer/
 * action logic is Business-specific.
 *
 * Known simplification: the wireframe's desktop layout splits multiple
 * operator threads into a list + detail side-by-side. This builds a single
 * mobile-first flow instead — a plain list when more than one thread
 * exists, tap through to the full-screen thread — since CLAUDE.md's stack
 * is mobile-first and a `lg:` split-panel enhancement can be added later
 * without changing this component's data flow.
 *
 * Known gap: the wireframe's a11y note calls for `aria-live="polite"` to
 * announce *new incoming* offers. There is no live-push/poll in this
 * increment (react-query refetches only on mount and after your own
 * actions), so the region is present (harmless, correctly structured) but
 * won't actually announce anything arriving from the other side while the
 * screen is open — a real-time channel is out of this increment's scope.
 */
export function NegotiationPage(): JSX.Element {
  const { jobId } = useParams<{ jobId: string }>();
  const { t } = useTranslation(['negotiation', 'jobs', 'errors']);
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null);

  const job = useQuery({
    queryKey: ['jobs', jobId],
    queryFn: () => jobsApi.get(jobId!),
    enabled: !!jobId,
    retry: false,
  });
  const threads = useQuery({
    queryKey: ['negotiation', 'threads', jobId],
    queryFn: () => negotiationApi.listThreads(jobId!),
    enabled: !!jobId,
    retry: false,
  });

  if (job.isLoading || threads.isLoading) return <PageLoader />;
  if (job.isError) {
    return <ErrorState message={localizeError(job.error, t)} onRetry={() => void job.refetch()} />;
  }
  if (threads.isError) {
    return (
      <ErrorState message={localizeError(threads.error, t)} onRetry={() => void threads.refetch()} />
    );
  }

  const jobData = job.data!;
  const threadList = threads.data!.data;
  const ref = jobData.id.slice(-6).toUpperCase();
  const route = [jobData.pickup_location?.address_text, jobData.destination_location?.address_text]
    .filter(Boolean)
    .join(' → ');

  const active =
    threadList.length === 1 ? threadList[0] : threadList.find((th) => th.thread_id === selectedThreadId);

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <div>
        <h1 className="text-h1 text-fg">{t('negotiation:title')}</h1>
        <p className="mt-1 text-body-sm text-fg-muted">{t('negotiation:jobRef', { ref })}</p>
      </div>

      <Card>
        <p className="text-body text-fg">{route || '—'}</p>
        {jobData.cargo?.description && (
          <p className="mt-1 text-body-sm text-fg-secondary">{jobData.cargo.description}</p>
        )}
      </Card>

      {threadList.length === 0 && (
        <EmptyState title={t('negotiation:noThreadsTitle')} description={t('negotiation:noThreadsBody')} />
      )}

      {threadList.length > 1 && !active && (
        <ThreadPicker threads={threadList} onSelect={setSelectedThreadId} count={threadList.length} />
      )}

      {active && (
        <>
          {threadList.length > 1 && (
            <button
              type="button"
              className="text-body-sm text-action-secondary-text underline"
              onClick={() => setSelectedThreadId(null)}
            >
              ← {t('negotiation:backToOffers')}
            </button>
          )}
          <ThreadDetail thread={active} jobId={jobId!} />
        </>
      )}
    </div>
  );
}

function ThreadPicker({
  threads,
  onSelect,
  count,
}: {
  threads: NegotiationThread[];
  onSelect: (id: string) => void;
  count: number;
}): JSX.Element {
  const { t } = useTranslation('negotiation');
  return (
    <div className="space-y-2">
      <h2 className="text-label text-fg-secondary">{t('negotiation:threadListTitle', { count })}</h2>
      <ul className="space-y-2">
        {threads.map((th) => (
          <li key={th.thread_id}>
            <button type="button" className="block w-full text-left" onClick={() => onSelect(th.thread_id)}>
              <Card interactive>
                <div className="flex items-center justify-between gap-3">
                  <span className="font-semibold text-fg">
                    {th.operator_display_name || t('negotiation:thread.operatorFallback')}
                  </span>
                  <span className="fk-numeric text-body text-fg-secondary">
                    {th.standing_offer ? formatKes(th.standing_offer.amount_kes) : '—'}
                  </span>
                </div>
              </Card>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function hhmm(iso: string): string {
  return new Date(iso).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
}

function ThreadDetail({ thread, jobId }: { thread: NegotiationThread; jobId: string }): JSX.Element {
  const { t } = useTranslation(['negotiation', 'errors']);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [composerOpen, setComposerOpen] = useState(false);
  const [amount, setAmount] = useState('');
  const [note, setNote] = useState('');
  const [amountError, setAmountError] = useState<string | null>(null);

  function invalidateAll(): void {
    void qc.invalidateQueries({ queryKey: ['negotiation', 'threads', jobId] });
    void qc.invalidateQueries({ queryKey: ['jobs', jobId] });
    void qc.invalidateQueries({ queryKey: ['jobs'] });
  }

  const counter = useMutation({
    mutationFn: () => {
      const minorUnits = parseKesToMinorUnits(amount);
      if (minorUnits === null) throw new Error('invalid-amount');
      return negotiationApi.counter(
        thread.thread_id,
        { amount_kes: minorUnits, note: note.trim() || undefined },
        crypto.randomUUID(),
      );
    },
    onSuccess: () => {
      setComposerOpen(false);
      setAmount('');
      setNote('');
      invalidateAll();
    },
  });

  const accept = useMutation({
    mutationFn: () =>
      negotiationApi.accept(
        thread.thread_id,
        thread.counterparty_offer ? { amount_kes: thread.counterparty_offer.amount_kes } : {},
        crypto.randomUUID(),
      ),
    onSuccess: (result) => {
      invalidateAll();
      if (result.confirmed) navigate(`/jobs/${jobId}`, { replace: true });
    },
    onError: (err) => {
      // The counterparty moved since we loaded the page — refresh so the
      // stale amount is never (silently) what gets accepted on a retry.
      if (err instanceof ApiError && err.code === 'invalid_offer') invalidateAll();
    },
  });

  const decline = useMutation({
    mutationFn: () => negotiationApi.decline(thread.thread_id, {}, crypto.randomUUID()),
    onSuccess: invalidateAll,
  });

  function submitCounter(): void {
    const minorUnits = parseKesToMinorUnits(amount);
    if (minorUnits === null) {
      setAmountError(t('negotiation:composer.amountInvalid'));
      return;
    }
    setAmountError(null);
    counter.mutate();
  }

  const agreed = thread.status !== 'ACTIVE' && thread.mutual_acceptance.reached;
  const declined = thread.status === 'CLOSED' && !thread.mutual_acceptance.reached;
  const superseded = thread.status === 'SUPERSEDED';
  const ownAcceptPending =
    thread.status === 'ACTIVE' &&
    thread.entries.some(
      (e) => e.actor_role === 'BUSINESS' && e.type === 'ACCEPT' && e.effective_status === 'ACTIVE',
    );

  return (
    <div className="space-y-4">
      <NegotiationThreadList
        entries={thread.entries}
        viewerRole="BUSINESS"
        operatorDisplayName={thread.operator_display_name}
        youLabel={t('negotiation:thread.you')}
        adminLabel={t('negotiation:thread.admin')}
        operatorFallbackLabel={t('negotiation:thread.operatorFallback')}
        statusLabelFor={(key) => t(`negotiation:thread.entryStatus.${key}`)}
        timeFor={hhmm}
      />

      {agreed && thread.mutual_acceptance.amount_kes != null && (
        <Card>
          <Alert tone="success">
            {t('negotiation:agreedBanner', { amount: formatKes(thread.mutual_acceptance.amount_kes) })}
          </Alert>
          <div className="mt-3">
            <Button fullWidth onClick={() => navigate(`/jobs/${jobId}`, { replace: true })}>
              {t('negotiation:openJob')}
            </Button>
          </div>
        </Card>
      )}

      {declined && (
        <Card>
          <Alert tone="info">{t('negotiation:closedDeclined')}</Alert>
        </Card>
      )}

      {superseded && (
        <Card>
          <Alert tone="warning">{t('negotiation:closedSuperseded')}</Alert>
        </Card>
      )}

      {thread.status === 'ACTIVE' && ownAcceptPending && (
        <Card>
          <p className="text-body text-fg-secondary">{t('negotiation:nothingToAcceptYet')}</p>
        </Card>
      )}

      {thread.status === 'ACTIVE' && !ownAcceptPending && (
        <Card>
          <div className="space-y-3">
            {thread.counterparty_offer && (
              <Button
                fullWidth
                loading={accept.isPending}
                onClick={() => accept.mutate()}
              >
                {t('negotiation:action.accept', { amount: formatKes(thread.counterparty_offer.amount_kes) })}
              </Button>
            )}

            {!composerOpen ? (
              <div className="flex gap-2">
                <Button variant="secondary" fullWidth onClick={() => setComposerOpen(true)}>
                  {t(
                    thread.counterparty_offer
                      ? 'negotiation:action.sendCounter'
                      : 'negotiation:action.askAgain',
                  )}
                </Button>
                <Button
                  variant="destructive"
                  loading={decline.isPending}
                  onClick={() => decline.mutate()}
                >
                  {t('negotiation:action.decline')}
                </Button>
              </div>
            ) : (
              <div className="space-y-3 rounded-md border border-line-strong bg-surface-sunken p-3">
                <Field label={t('negotiation:composer.amountLabel')} error={amountError ?? undefined}>
                  {(props) => (
                    <Input
                      {...props}
                      inputMode="numeric"
                      value={amount}
                      onChange={(e) => setAmount(e.target.value)}
                    />
                  )}
                </Field>
                <Field label={t('negotiation:composer.noteLabel')}>
                  {(props) => (
                    <Input {...props} value={note} onChange={(e) => setNote(e.target.value)} />
                  )}
                </Field>
                <div className="flex gap-2">
                  <Button
                    variant="secondary"
                    size="compact"
                    onClick={() => setComposerOpen(false)}
                    disabled={counter.isPending}
                  >
                    {t('jobs:create.back')}
                  </Button>
                  <Button size="compact" loading={counter.isPending} onClick={submitCounter}>
                    {t('negotiation:composer.send')}
                  </Button>
                </div>
              </div>
            )}
          </div>
        </Card>
      )}

      {(counter.isError || accept.isError || decline.isError) && (
        <Alert tone="danger">
          {localizeError(counter.error ?? accept.error ?? decline.error, t)}
        </Alert>
      )}
    </div>
  );
}
