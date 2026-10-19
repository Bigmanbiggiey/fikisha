import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Link, useSearchParams } from 'react-router-dom';

import { Card } from '@/components/Card';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { PageLoader } from '@/components/PageLoader';
import { StatusBadge } from '@/components/StatusBadge';
import { formatDateTime } from '@/services/datetime';
import { localizeError } from '@/services/errorMessage';

import { verificationApi, type ApplicantKind } from './verificationApi';

const KINDS: readonly ApplicantKind[] = ['OPERATOR', 'BUSINESS', 'GROUP'];

/**
 * The verification queue by applicant (assessment 2026-10-19 part 5): a tab
 * per kind of user at the top, then one row per operator, business or group
 * waiting for review, oldest first. A row opens everything they submitted.
 */
export function VerificationQueuePage(): JSX.Element {
  const { t } = useTranslation(['org', 'errors']);
  const [params, setParams] = useSearchParams();
  const kind = (KINDS as readonly string[]).includes(params.get('kind') ?? '')
    ? (params.get('kind') as ApplicantKind)
    : 'OPERATOR';
  const list = useQuery({
    queryKey: ['verification-applicants', kind],
    queryFn: () => verificationApi.applicants(kind),
    retry: false,
  });

  return (
    <div className="space-y-5">
      <h1 className="text-h1 text-fg">{t('org:verification.queueTitle')}</h1>

      <div role="tablist" aria-label={t('org:applicants.tabsLabel')} className="flex flex-wrap gap-2">
        {KINDS.map((k) => (
          <button
            key={k}
            type="button"
            role="tab"
            aria-selected={k === kind}
            onClick={() => setParams({ kind: k }, { replace: true })}
            className={
              k === kind
                ? 'min-h-target rounded-md bg-action-primary px-4 text-body-sm font-semibold text-action-on-primary'
                : 'min-h-target rounded-md border border-line-strong bg-surface-card px-4 text-body-sm text-fg'
            }
          >
            {t(`org:applicants.tab.${k}`)}
          </button>
        ))}
      </div>

      <div role="tabpanel">
        {list.isLoading ? (
          <PageLoader />
        ) : list.isError ? (
          <ErrorState message={localizeError(list.error, t)} error={list.error} onRetry={() => void list.refetch()} />
        ) : list.data && list.data.data.length > 0 ? (
          <ul className="space-y-2">
            {list.data.data.map((a) => (
              <li key={a.id}>
                <Link to={`/verification/applicants/${a.kind}/${a.id}`} className="block rounded-md">
                  <Card interactive>
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-semibold text-fg">{a.name}</span>
                      <span className="flex flex-wrap items-center gap-2">
                        <StatusBadge
                          tone={a.status === 'ACTIVE' || a.status === 'VERIFIED' ? 'success' : 'warning'}
                          label={t(`org:applicants.status.${a.status}`, { defaultValue: a.status })}
                        />
                        {a.open_count > 0 && (
                          <StatusBadge tone="brand" label={t('org:applicants.openCount', { count: a.open_count })} />
                        )}
                      </span>
                    </div>
                    <p className="mt-1 text-body-sm text-fg-muted">
                      {a.required_count !== undefined &&
                        `${t('org:applicants.checks', { done: a.verified_count, total: a.required_count })} · `}
                      {t('org:applicants.waitingSince', {
                        when: formatDateTime(a.oldest_open_at ?? a.created_at),
                      })}
                    </p>
                  </Card>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState title={t('org:verification.queueEmpty')} />
        )}
      </div>
    </div>
  );
}
