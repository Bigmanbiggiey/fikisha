import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { JobCard } from '@/components/JobCard';
import { PageLoader } from '@/components/PageLoader';
import { localizeError } from '@/services/errorMessage';

import { jobReference } from './jobHelpers';
import { jobsApi } from './jobsApi';
import { formatKes } from './money';
import { VALUE_BANDS, type ValueBand } from './types';

/**
 * Work discovery (`design-phase-3-wireframes.md` §7.2). Individual-operator-
 * only interim matching — server-scoped to the operator's own vehicle
 * classes (`jobs.discovery.open_jobs_for`), never "the whole marketplace".
 * Ineligible jobs are shown, not hidden, with a concrete reason.
 */
export function WorkListPage(): JSX.Element {
  const { t } = useTranslation(['jobs', 'errors']);
  const navigate = useNavigate();
  const [valueBand, setValueBand] = useState<ValueBand | ''>('');

  const jobs = useQuery({
    queryKey: ['jobs', 'opportunities', valueBand],
    queryFn: () => jobsApi.discover(valueBand ? { value_band: valueBand } : {}),
    retry: false,
  });

  return (
    <div className="space-y-4">
      <h1 className="text-h1 text-fg">{t('jobs:work.title')}</h1>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => setValueBand('')}
          className={`rounded-full border px-3 py-1 text-body-sm ${
            valueBand === '' ? 'border-action-primary bg-surface-brand-tint text-fg' : 'border-line text-fg-secondary'
          }`}
        >
          {t('jobs:work.allBands')}
        </button>
        {VALUE_BANDS.map((band) => (
          <button
            key={band}
            type="button"
            onClick={() => setValueBand(band)}
            className={`rounded-full border px-3 py-1 text-body-sm ${
              valueBand === band
                ? 'border-action-primary bg-surface-brand-tint text-fg'
                : 'border-line text-fg-secondary'
            }`}
          >
            {t(`jobs:opportunity.band.${band}`)}
          </button>
        ))}
      </div>

      {jobs.isLoading ? (
        <PageLoader />
      ) : jobs.isError ? (
        <ErrorState message={localizeError(jobs.error, t)} onRetry={() => void jobs.refetch()} />
      ) : (jobs.data?.data ?? []).length === 0 ? (
        <EmptyState title={t('jobs:work.emptyTitle')} description={t('jobs:work.emptyBody')} />
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {(jobs.data?.data ?? []).map((job) => (
            <JobCard
              key={job.id}
              reference={jobReference(job.id)}
              state={job.status}
              stateLabel={t(`jobs:status.${job.status}`)}
              route={{
                from: job.pickup_location?.address_text || '—',
                to: job.destination_location?.address_text || '—',
              }}
              cargo={job.cargo?.description ?? ''}
              price={job.proposed_price_kes != null ? formatKes(job.proposed_price_kes) : undefined}
              nextActionHint={
                job.eligibility.eligible
                  ? t('jobs:work.canTake')
                  : (job.eligibility.reasons[0] ?? t('jobs:work.needsMore'))
              }
              onClick={() => navigate(`/work/${job.id}`)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
