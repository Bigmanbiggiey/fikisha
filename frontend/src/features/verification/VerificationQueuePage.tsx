import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { Card } from '@/components/Card';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { PageLoader } from '@/components/PageLoader';
import { VerificationPill } from '@/components/VerificationPill';
import type { VerificationState } from '@/design/tokens';
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
      <h1 className="text-h1 text-fg">{t('org:verification.queueTitle')}</h1>

      {queue.isLoading ? (
        <PageLoader />
      ) : queue.isError ? (
        <ErrorState message={localizeError(queue.error, t)} onRetry={() => void queue.refetch()} />
      ) : queue.data && queue.data.data.length > 0 ? (
        <ul className="space-y-2">
          {queue.data.data.map((r) => (
            <li key={r.id}>
              <Link to={`/verification/${r.id}`} className="block rounded-md">
                <Card interactive>
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-semibold text-fg">
                      {r.subject_type} · {r.domain}
                    </span>
                    <VerificationPill state={r.state as VerificationState} hideDomain />
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
