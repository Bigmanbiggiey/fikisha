import { useInfiniteQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Link, useSearchParams } from 'react-router-dom';

import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { JobStatusChip } from '@/components/JobStatusChip';
import { PageLoader } from '@/components/PageLoader';
import { JOB_STATUSES, VALUE_BANDS, type JobStatus, type ValueBand } from '@/features/jobs/types';
import { localizeError } from '@/services/errorMessage';

import { JobReferenceJump } from './JobReferenceJump';
import { cursorFrom, opsApi } from './opsApi';
import type { AttentionFilter, MonitorFilters, OpsJobRow } from './types';

const ATTENTION: AttentionFilter[] = ['disputed', 'failed', 'high_value_pending', 'stale'];
const selectClass =
  'block min-h-target w-full rounded-md border border-line-strong bg-surface-input px-3 text-body text-fg';

/**
 * §18.2 Job monitoring — filters (state, band, attention/age) and the
 * reference quick jump, as URL search params so a filtered view is
 * linkable. Desktop: a real `<table>` (the first in the codebase, kept
 * page-local until a second screen needs one). Small screens: one card per
 * job. Rows carry no contact details — those go through the audited reveal
 * on Job Detail.
 */
export function OpsJobsPage(): JSX.Element {
  const { t } = useTranslation(['ops', 'jobs', 'errors']);
  const [params, setParams] = useSearchParams();

  const filters: MonitorFilters = {
    status: params.get('status') ? [params.get('status') as JobStatus] : undefined,
    value_band: (params.get('value_band') as ValueBand | null) ?? undefined,
    attention: (params.get('attention') as AttentionFilter | null) ?? undefined,
    ref: params.get('ref') ?? undefined,
  };

  const jobs = useInfiniteQuery({
    queryKey: ['ops', 'monitor', filters],
    queryFn: ({ pageParam }) => opsApi.monitor(filters, pageParam),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => cursorFrom(last.page.next_cursor),
    retry: false,
  });

  function setFilter(key: string, value: string): void {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  }

  const rows: OpsJobRow[] = jobs.data?.pages.flatMap((p) => p.data) ?? [];

  return (
    <div className="space-y-5">
      <h1 className="text-h1 text-fg">{t('ops:monitor.title')}</h1>

      <Card className="space-y-4">
        <JobReferenceJump />
        <fieldset className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <legend className="sr-only">{t('ops:monitor.filters')}</legend>
          <FilterSelect
            id="f-status"
            label={t('ops:monitor.status')}
            value={params.get('status') ?? ''}
            onChange={(v) => setFilter('status', v)}
            options={[
              ['', t('ops:monitor.anyStatus')],
              ...JOB_STATUSES.map((s) => [s, t(`jobs:status.${s}`)] as [string, string]),
            ]}
          />
          <FilterSelect
            id="f-band"
            label={t('ops:monitor.band')}
            value={params.get('value_band') ?? ''}
            onChange={(v) => setFilter('value_band', v)}
            options={[
              ['', t('ops:monitor.anyBand')],
              ...VALUE_BANDS.map((b) => [b, t(`ops:band.${b}`)] as [string, string]),
            ]}
          />
          <FilterSelect
            id="f-attention"
            label={t('ops:monitor.attention')}
            value={params.get('attention') ?? ''}
            onChange={(v) => setFilter('attention', v)}
            options={[
              ['', t('ops:monitor.anyAttention')],
              ...ATTENTION.map((a) => [a, t(`ops:monitor.attentionOption.${a}`)] as [string, string]),
            ]}
          />
        </fieldset>
      </Card>

      {jobs.isLoading ? (
        <PageLoader />
      ) : jobs.isError ? (
        <ErrorState message={localizeError(jobs.error, t)} onRetry={() => void jobs.refetch()} />
      ) : rows.length === 0 ? (
        <EmptyState title={t('ops:monitor.empty')} />
      ) : (
        <>
          <div className="hidden overflow-x-auto md:block">
            <table className="w-full border-collapse text-left text-body-sm">
              <caption className="sr-only">{t('ops:monitor.title')}</caption>
              <thead>
                <tr className="border-b border-line-strong text-fg-secondary">
                  <th scope="col" className="py-2 pr-3">{t('ops:monitor.col.reference')}</th>
                  <th scope="col" className="py-2 pr-3">{t('ops:monitor.col.status')}</th>
                  <th scope="col" className="py-2 pr-3">{t('ops:monitor.col.band')}</th>
                  <th scope="col" className="py-2 pr-3">{t('ops:monitor.col.business')}</th>
                  <th scope="col" className="py-2 pr-3">{t('ops:monitor.col.route')}</th>
                  <th scope="col" className="py-2">{t('ops:monitor.col.lastChange')}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id} className="border-b border-line align-top">
                    <th scope="row" className="py-2 pr-3 font-semibold">
                      <Link
                        to={`/jobs/${row.id}`}
                        className="fk-numeric text-action-secondary-text underline"
                        aria-label={t('ops:monitor.open', { ref: row.reference })}
                      >
                        {row.reference}
                      </Link>
                    </th>
                    <td className="py-2 pr-3">
                      <JobStatusChip state={row.status} label={t(`jobs:status.${row.status}`)} />
                    </td>
                    <td className="py-2 pr-3 text-fg">{t(`ops:band.${row.value_band ?? 'none'}`)}</td>
                    <td className="py-2 pr-3 text-fg">{row.business_name}</td>
                    <td className="py-2 pr-3 text-fg-secondary">
                      {row.pickup_area || '—'} → {row.destination_area || '—'}
                    </td>
                    <td className="py-2 text-fg-muted">{new Date(row.last_changed_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <ul className="space-y-2 md:hidden">
            {rows.map((row) => (
              <li key={row.id}>
                <Card className="space-y-1">
                  <Link
                    to={`/jobs/${row.id}`}
                    className="fk-numeric text-body font-semibold text-fg"
                    aria-label={t('ops:monitor.open', { ref: row.reference })}
                  >
                    {row.reference}
                  </Link>
                  <div className="flex flex-wrap items-center gap-2">
                    <JobStatusChip state={row.status} label={t(`jobs:status.${row.status}`)} />
                    <span className="text-body-sm text-fg-secondary">{t(`ops:band.${row.value_band ?? 'none'}`)}</span>
                  </div>
                  <p className="text-body-sm text-fg">{row.business_name}</p>
                  <p className="text-body-sm text-fg-muted">{new Date(row.last_changed_at).toLocaleString()}</p>
                </Card>
              </li>
            ))}
          </ul>

          {jobs.hasNextPage && (
            <div className="flex justify-center">
              <Button variant="secondary" loading={jobs.isFetchingNextPage} onClick={() => void jobs.fetchNextPage()}>
                {t('ops:monitor.loadMore')}
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function FilterSelect({
  id,
  label,
  value,
  onChange,
  options,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: [string, string][];
}): JSX.Element {
  return (
    <div className="space-y-1">
      <label htmlFor={id} className="block text-label text-fg-secondary">
        {label}
      </label>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)} className={selectClass}>
        {options.map(([v, text]) => (
          <option key={v || 'any'} value={v}>
            {text}
          </option>
        ))}
      </select>
    </div>
  );
}
