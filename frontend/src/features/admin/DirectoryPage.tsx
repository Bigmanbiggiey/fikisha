import { useInfiniteQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useSearchParams } from 'react-router-dom';

import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { Input } from '@/components/Input';
import { PageLoader } from '@/components/PageLoader';
import { cn } from '@/components/cn';
import { FilterSelect } from '@/features/ops/FilterSelect';
import { localizeError } from '@/services/errorMessage';

import { adminApi, cursorFrom } from './adminApi';
import { AccountStateBadge } from './AccountStateBadge';
import { KIND_STATES, type DirectoryKind, type DirectoryRow } from './types';

const KINDS: DirectoryKind[] = ['businesses', 'operators', 'groups'];

function isKind(value: string | null): value is DirectoryKind {
  return KINDS.includes(value as DirectoryKind);
}

/**
 * Users & Organizations (P3 §19.5, Increment 9 D-6): every business,
 * operator and group, Platform Admin only. Phones are masked here; the full
 * number is an audited reveal on the detail page. Filters live in the URL.
 */
export function DirectoryPage(): JSX.Element {
  const { t } = useTranslation(['admin', 'errors']);
  const [params, setParams] = useSearchParams();
  const kind: DirectoryKind = isKind(params.get('kind')) ? (params.get('kind') as DirectoryKind) : 'businesses';
  const state = params.get('state') ?? '';
  const q = params.get('q') ?? '';
  const [search, setSearch] = useState(q);

  const list = useInfiniteQuery({
    queryKey: ['admin', 'directory', kind, { q, state }],
    queryFn: ({ pageParam }) => adminApi.directory(kind, { q, state }, pageParam),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => cursorFrom(last.page.next_cursor),
    retry: false,
  });

  function update(changes: Record<string, string>): void {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    setParams(next, { replace: true });
  }

  const rows: DirectoryRow[] = list.data?.pages.flatMap((p) => p.data) ?? [];

  return (
    <div className="space-y-5">
      <h1 className="text-h1 text-fg">{t('admin:directory.title')}</h1>

      <div className="flex flex-wrap gap-2" role="group" aria-label={t('admin:directory.kindLabel')}>
        {KINDS.map((k) => (
          <button
            key={k}
            type="button"
            aria-pressed={kind === k}
            onClick={() => update({ kind: k, state: '' })}
            className={cn(
              'min-h-target rounded-md border px-3 text-body',
              kind === k
                ? 'border-action-primary bg-surface-brand-tint font-semibold text-action-primary'
                : 'border-line-strong bg-surface-card text-fg-secondary',
            )}
          >
            {t(`admin:directory.kind.${k}`)}
          </button>
        ))}
      </div>

      <Card>
        <form
          className="grid grid-cols-1 gap-3 md:grid-cols-[2fr_1fr_auto] md:items-end"
          onSubmit={(e) => {
            e.preventDefault();
            update({ q: search.trim() });
          }}
        >
          <div className="space-y-1">
            <label htmlFor="directory-search" className="block text-label text-fg-secondary">
              {t('admin:directory.search')}
            </label>
            <Input id="directory-search" value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
          <FilterSelect
            id="directory-state"
            label={t('admin:directory.state')}
            value={state}
            onChange={(v) => update({ state: v })}
            options={[
              ['', t('admin:directory.anyState')],
              ...KIND_STATES[kind].map((s) => [s, t(`admin:state.${s}`)] as [string, string]),
            ]}
          />
          <Button type="submit" variant="secondary">
            {t('admin:directory.searchGo')}
          </Button>
        </form>
      </Card>

      {list.isLoading ? (
        <PageLoader />
      ) : list.isError ? (
        <ErrorState message={localizeError(list.error, t)} error={list.error} onRetry={() => void list.refetch()} />
      ) : rows.length === 0 ? (
        <EmptyState title={t('admin:directory.empty')} />
      ) : (
        <ul className="divide-y divide-line rounded-md border border-line bg-surface-card">
          {rows.map((row) => (
            <li key={row.id}>
              <Link
                to={`/admin/directory/${kind}/${row.id}`}
                className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 hover:bg-surface-sunken"
              >
                <span className="min-w-0">
                  <span className="block text-body font-semibold text-fg">{row.name}</span>
                  <span className="block text-body-sm text-fg-muted">
                    {[row.phone, row.member_count != null ? t('admin:directory.members', { count: row.member_count }) : null]
                      .filter(Boolean)
                      .join(' · ')}
                  </span>
                </span>
                <AccountStateBadge state={row.state} />
              </Link>
            </li>
          ))}
        </ul>
      )}

      {list.hasNextPage && (
        <div className="flex justify-center">
          <Button variant="secondary" loading={list.isFetchingNextPage} onClick={() => void list.fetchNextPage()}>
            {t('admin:directory.loadMore')}
          </Button>
        </div>
      )}
    </div>
  );
}
