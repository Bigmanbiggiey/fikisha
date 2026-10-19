import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ErrorState } from '@/components/ErrorState';
import { PageLoader } from '@/components/PageLoader';
import { StatusBadge } from '@/components/StatusBadge';
import { formatKes } from '@/features/jobs/money';
import { formatDate } from '@/services/datetime';
import { localizeError } from '@/services/errorMessage';

import { periodLabel, stateBadge } from './statementFormat';
import { LinesCard, PaymentsCard, Row, SummaryCard } from './StatementParts';
import { statementsApi, statementsQueryKey } from './statementsApi';
import type { StatementDetail } from './types';

/**
 * One weekly statement (P3 §6.5 / §7.5, Commission & Statements S-2): the
 * jobs billed, any credits, what has been paid and where to pay. Labelled
 * "not a tax invoice" until eTIMS exists (D-1). The paybill number shows
 * once Fikisha sets it; until then "details to follow" (D-3). Opening it
 * marks it seen (D-6). Printable: the navigation hides when printing.
 */
export function StatementDetailPage(): JSX.Element {
  const { statementId } = useParams<{ statementId: string }>();
  const { t, i18n } = useTranslation(['statements', 'common', 'errors']);
  const qc = useQueryClient();

  const statement = useQuery({
    queryKey: [...statementsQueryKey, 'detail', statementId],
    queryFn: () => statementsApi.get(statementId!),
    enabled: !!statementId,
    retry: false,
  });

  const markSeen = useMutation({
    mutationFn: () => statementsApi.markSeen(statementId!),
    onSuccess: () => void qc.invalidateQueries({ queryKey: [...statementsQueryKey, 'list'] }),
  });
  const loaded = statement.isSuccess;
  const { mutate } = markSeen;
  useEffect(() => {
    if (loaded) mutate();
  }, [loaded, mutate]);

  if (statement.isLoading) return <PageLoader />;
  if (statement.isError) {
    return (
      <ErrorState
        message={localizeError(statement.error, t)}
        error={statement.error}
        onRetry={() => void statement.refetch()}
      />
    );
  }
  const s: StatementDetail = statement.data!;

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <StatementHeading s={s} />

      <Alert tone="info">{t('statements:detail.notTaxInvoice')}</Alert>

      <SummaryCard s={s} />

      {s.outstanding_kes > 0 && (
        <Card>
          <h2 className="text-label text-fg-secondary">{t('statements:detail.howToPay')}</h2>
          {s.payment.paybill_number ? (
            <dl className="mt-2 space-y-1 text-body">
              <Row label={t('statements:detail.paybill')} value={s.payment.paybill_number} />
              <Row label={t('statements:detail.account')} value={s.payment.account_reference} />
              <Row label={t('statements:detail.amount')} value={formatKes(s.outstanding_kes)} />
            </dl>
          ) : (
            <p className="mt-2 text-body text-fg">
              {t('statements:detail.detailsToFollow', { reference: s.payment.account_reference })}
            </p>
          )}
          <p className="mt-2 text-body-sm text-fg-muted">{t('statements:detail.payNote')}</p>
        </Card>
      )}

      <LinesCard s={s} />
      <PaymentsCard s={s} />

      <p className="text-caption text-fg-muted">
        {t('statements:detail.generated', {
          date: formatDate(s.generated_at, i18n.resolvedLanguage),
        })}
      </p>
    </div>
  );
}

/** Wordmark (print only), reference, week, payee, state badge and Print.
 * ``actions`` lets the staff page add its own buttons. */
export function StatementHeading({
  s,
  actions,
}: {
  s: StatementDetail;
  actions?: ReactNode;
}): JSX.Element {
  const { t, i18n } = useTranslation(['statements', 'common']);
  const badge = stateBadge(s);
  return (
    <>
      {/* the printed copy carries the wordmark (P3 §6.5); on screen the
          top bar already does */}
      <p className="hidden text-h3 font-semibold text-action-primary print:block">
        {t('common:appName')}
      </p>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-label text-fg-secondary">{t('statements:detail.eyebrow')}</p>
          <h1 className="fk-numeric text-h1 text-fg">{s.reference}</h1>
          <p className="mt-1 text-body text-fg-secondary">
            {periodLabel(s, i18n.resolvedLanguage)}
          </p>
          {s.payee.name && <p className="text-body-sm text-fg-muted">{s.payee.name}</p>}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge tone={badge.tone} label={t(`statements:state.${badge.key}`)} />
          {actions}
          <Button variant="secondary" className="print:hidden" onClick={() => window.print()}>
            {t('statements:detail.print')}
          </Button>
        </div>
      </div>
    </>
  );
}
