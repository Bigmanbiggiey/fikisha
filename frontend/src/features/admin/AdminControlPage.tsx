import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Card } from '@/components/Card';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { PageLoader } from '@/components/PageLoader';
import { useOnline } from '@/design/useOnline';
import { opsApi } from '@/features/ops/opsApi';
import { Queue, QueueRow } from '@/features/ops/Queue';
import { StatementsSummaryCard } from '@/features/statements/StatementsSummaryCard';
import { CancellationFlagsCard } from '@/features/ops/CancellationFlagsCard';
import { TierReviewsCard } from '@/features/trust/TierReviewsCard';
import { localizeError } from '@/services/errorMessage';
import { formatDateTime } from '@/services/datetime';

function ageOrder<T extends { created_at: string }>(rows: T[]): T[] {
  return [...rows].sort((a, b) => a.created_at.localeCompare(b.created_at));
}

/**
 * Platform Admin "Control" (P3 §19.1, Increment 9b, the part buildable
 * before the founder's Increment 9 decisions): only the queues that need a
 * Platform Administrator, oldest first. Everything an Operations Officer
 * can clear stays on the Operations overview, linked below.
 *
 * Built on the existing Ops queues (`/ops/disputes`, `/ops/high-value`),
 * filtered to `needs_platform_admin`: disputes above the Standard band, and
 * Very High value jobs awaiting per-job approval. The other §19.1 queues
 * (resume requests, suspension and configuration requests) have no backend
 * yet and are not shown (`design-phase-6-increment-9-scope.md` D-5).
 * The filters run on the first page each endpoint returns; when the
 * endpoint has more, the count reads "N+". UX only: the server authorises
 * every action.
 */
export function AdminControlPage(): JSX.Element {
  const { t } = useTranslation(['ops', 'incidents', 'errors']);
  const online = useOnline();

  const disputes = useQuery({
    queryKey: ['ops', 'disputes'],
    queryFn: opsApi.disputeQueue,
    retry: false,
  });
  const highValue = useQuery({
    queryKey: ['ops', 'high-value'],
    queryFn: () => opsApi.highValueQueue(),
    retry: false,
  });

  if (disputes.isLoading || highValue.isLoading) return <PageLoader />;
  const failed = disputes.error ?? highValue.error;
  if (failed) {
    return (
      <ErrorState
        message={localizeError(failed, t)}
        error={failed}
        onRetry={() => {
          void disputes.refetch();
          void highValue.refetch();
        }}
      />
    );
  }

  const dis = ageOrder((disputes.data?.data ?? []).filter((r) => r.needs_platform_admin));
  const hv = ageOrder((highValue.data?.data ?? []).filter((r) => r.needs_platform_admin));
  const disMore = !!disputes.data?.page.next_cursor;
  const hvMore = !!highValue.data?.page.next_cursor;
  const allClear = dis.length + hv.length === 0 && !disMore && !hvMore;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-h1 text-fg">{t('ops:control.title')}</h1>
        <p className="mt-1 text-body-sm text-fg-muted">{t('ops:control.subtitle')}</p>
      </div>

      {!online && <Alert tone="warning">{t('ops:overview.reconnect')}</Alert>}

      {allClear ? (
        <EmptyState title={t('ops:control.nothing')} description={t('ops:control.nothingHint')} />
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Queue title={t('ops:control.disputes')} count={dis.length} more={disMore}>
            {dis.slice(0, 8).map((row) => (
              <QueueRow
                key={row.id}
                to={`/disputes/${row.id}`}
                title={`${row.job_reference} · ${t(`ops:band.${row.value_band}`)}`}
                meta={`${t(`incidents:detail.status.${row.status}`)} · ${formatDateTime(row.created_at)}`}
              />
            ))}
          </Queue>

          <Queue
            title={t('ops:control.highValue')}
            count={hv.length}
            more={hvMore}
            viewAll="/ops/high-value"
          >
            {hv.slice(0, 8).map((row) => (
              <QueueRow
                key={row.id}
                to="/ops/high-value"
                title={`${row.reference} · ${t(`ops:band.${row.value_band ?? 'none'}`)}`}
                meta={row.business_name}
              />
            ))}
          </Queue>
        </div>
      )}

      <TierReviewsCard />

      <CancellationFlagsCard />

      <StatementsSummaryCard />

      <Card>
        <p className="text-body-sm text-fg-secondary">{t('ops:control.opsHint')}</p>
        <Link
          to="/ops"
          className="mt-2 inline-block text-body text-action-secondary-text underline"
        >
          {t('ops:control.openOps')}
        </Link>
      </Card>
    </div>
  );
}
