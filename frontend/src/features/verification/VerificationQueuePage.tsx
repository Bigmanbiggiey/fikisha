import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { Card } from '@/components/Card';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { PageLoader } from '@/components/PageLoader';
import { StatusBadge } from '@/components/StatusBadge';
import { localizeError } from '@/services/errorMessage';

import { verificationApi } from './verificationApi';

export function VerificationQueuePage(): JSX.Element {
  const { t } = useTranslation(['org', 'errors']);
  const queue = useQuery({
    queryKey: ['verification-queue'],
    queryFn: verificationApi.queue,
    retry: false,
  });

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold text-slate-900">{t('org:verification.queueTitle')}</h1>

      {queue.isLoading ? (
        <PageLoader />
      ) : queue.isError ? (
        <ErrorState message={localizeError(queue.error, t)} onRetry={() => void queue.refetch()} />
      ) : queue.data && queue.data.data.length > 0 ? (
        <ul className="space-y-2">
          {queue.data.data.map((r) => (
            <li key={r.id}>
              <Link to={`/verification/${r.id}`} className="block">
                <Card className="transition hover:border-brand-300">
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-medium text-slate-900">
                      {r.subject_type} · {r.domain}
                    </span>
                    <StatusBadge label={r.state} />
                  </div>
                </Card>
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState title={t('org:verification.queueEmpty')} />
      )}
    </div>
  );
}
