import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { ErrorState } from '@/components/ErrorState';
import { PageLoader } from '@/components/PageLoader';
import { AdminActionDialog } from '@/features/admin/AdminActionDialog';
import { useAuth } from '@/features/auth/useAuth';
import { isPlatformAdmin } from '@/features/auth/staff';
import { formatKes } from '@/features/jobs/money';
import { formatDate } from '@/services/datetime';
import { localizeError } from '@/services/errorMessage';

import { RecordPaymentDialog } from './RecordPaymentDialog';
import { StatementHeading } from './StatementDetailPage';
import { LinesCard, PaymentsCard, SummaryCard } from './StatementParts';
import { statementsApi, statementsQueryKey } from './statementsApi';
import type { PaymentInput, StatementDetail, StatementSettlement } from './types';

/**
 * One statement, staff view (P3 §19.4, Commission & Statements S-3). The
 * same breakdown the payee sees, plus the payments with who-noted-what. A
 * Platform Admin records a payment (D-4) or reverses a mistaken one with a
 * reason (D-5); both ask for a fresh authenticator code. Operations
 * Officers see it read-only.
 */
export function AdminStatementDetailPage(): JSX.Element {
  const { statementId } = useParams<{ statementId: string }>();
  const { t, i18n } = useTranslation(['statements', 'errors']);
  const { user } = useAuth();
  const canAct = isPlatformAdmin(user);
  const qc = useQueryClient();
  const [recordOpen, setRecordOpen] = useState(false);
  const [reversing, setReversing] = useState<StatementSettlement | null>(null);
  const [done, setDone] = useState<string | null>(null);

  const queryKey = [...statementsQueryKey, 'admin', 'detail', statementId];
  const statement = useQuery({
    queryKey,
    queryFn: () => statementsApi.adminGet(statementId!),
    enabled: !!statementId,
    retry: false,
  });

  function applied(updated: StatementDetail, message: string): void {
    qc.setQueryData(queryKey, updated);
    void qc.invalidateQueries({ queryKey: [...statementsQueryKey, 'admin'] });
    setDone(message);
  }

  const record = useMutation({
    mutationFn: (input: PaymentInput) => statementsApi.recordPayment(statementId!, input),
    onSuccess: (updated, input) => {
      setRecordOpen(false);
      applied(
        updated,
        t('statements:admin.recorded', {
          amount: formatKes(input.amount_kes),
          ref: input.payment_ref,
        }),
      );
    },
  });
  const reverse = useMutation({
    mutationFn: ({ paymentId, reason }: { paymentId: string; reason: string }) =>
      statementsApi.reversePayment(statementId!, paymentId, reason),
    onSuccess: (updated) => {
      const ref = reversing?.payment_ref ?? '';
      setReversing(null);
      applied(updated, t('statements:admin.reversed', { ref }));
    },
  });

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
  const s = statement.data!;

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <Link
        to="/ops/statements"
        className="text-body-sm text-action-secondary-text underline print:hidden"
      >
        {t('statements:admin.backToList')}
      </Link>

      <StatementHeading
        s={s}
        actions={
          canAct &&
          s.outstanding_kes > 0 && (
            <Button
              className="print:hidden"
              onClick={() => {
                record.reset();
                setRecordOpen(true);
              }}
            >
              {t('statements:admin.record')}
            </Button>
          )
        }
      />

      {done && <Alert tone="success">{done}</Alert>}
      {s.overdue && <Alert tone="warning">{t('statements:admin.overdueNote')}</Alert>}

      <SummaryCard s={s} staff />
      <PaymentsCard
        s={s}
        empty={t('statements:admin.noPayments')}
        action={(p) =>
          canAct && p.kind === 'PAYMENT' && !p.reversed ? (
            <Button
              variant="secondary"
              className="print:hidden"
              onClick={() => {
                reverse.reset();
                setReversing(p);
              }}
            >
              {t('statements:admin.reverse')}
            </Button>
          ) : null
        }
      />
      <LinesCard s={s} />

      <p className="text-caption text-fg-muted">
        {t('statements:detail.generated', {
          date: formatDate(s.generated_at, i18n.resolvedLanguage),
        })}{' '}
        · {t('statements:admin.paymentAccount', { reference: s.payment.account_reference })}
      </p>

      {canAct && (
        <>
          <RecordPaymentDialog
            open={recordOpen}
            statement={s}
            pending={record.isPending}
            error={record.error}
            onClose={() => setRecordOpen(false)}
            onConfirm={(input) => record.mutate(input)}
          />
          <AdminActionDialog
            open={reversing !== null}
            onClose={() => setReversing(null)}
            title={t('statements:admin.reverseTitle')}
            restatement={t('statements:admin.reverseRestate', {
              amount: reversing ? formatKes(reversing.amount_kes) : '',
              ref: reversing?.payment_ref ?? '',
              reference: s.reference,
            })}
            confirmLabel={t('statements:admin.reverseConfirm')}
            pending={reverse.isPending}
            error={reverse.error}
            onConfirm={({ reason }) =>
              reversing && reverse.mutate({ paymentId: reversing.id, reason })
            }
          />
        </>
      )}
    </div>
  );
}
