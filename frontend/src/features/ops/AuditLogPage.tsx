import { useInfiniteQuery } from '@tanstack/react-query';
import { type FormEvent, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { Input } from '@/components/Input';
import { PageLoader } from '@/components/PageLoader';
import { localizeError } from '@/services/errorMessage';

import { cursorFrom, opsApi } from './opsApi';
import type { AuditFilters } from './types';

const EMPTY: AuditFilters = {};
const FIELDS: { key: keyof AuditFilters; label: string; type?: string }[] = [
  { key: 'entity_type', label: 'ops:audit.entityType' },
  { key: 'entity_id', label: 'ops:audit.entityId' },
  { key: 'actor_user', label: 'ops:audit.actor' },
  { key: 'action', label: 'ops:audit.action' },
  { key: 'from', label: 'ops:audit.from', type: 'datetime-local' },
  { key: 'to', label: 'ops:audit.to', type: 'datetime-local' },
];

function toIso(local: string | undefined): string | undefined {
  return local ? new Date(local).toISOString() : undefined;
}

/**
 * §18.5 Audit / activity (read) — who · what · when · which resource.
 * Read-only; not an end-user feature. The *scope* (an Ops Officer sees the
 * Ops remit only — founder decision 2026-09-23) is applied server-side;
 * this screen just shows whatever the server returns.
 */
export function AuditLogPage(): JSX.Element {
  const { t } = useTranslation(['ops', 'errors']);
  const [draft, setDraft] = useState<AuditFilters>(EMPTY);
  const [applied, setApplied] = useState<AuditFilters>(EMPTY);

  const entries = useInfiniteQuery({
    queryKey: ['ops', 'audit', applied],
    queryFn: ({ pageParam }) => opsApi.audit(applied, pageParam),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => cursorFrom(last.page.next_cursor),
    retry: false,
  });

  function onSubmit(e: FormEvent): void {
    e.preventDefault();
    setApplied({ ...draft, from: toIso(draft.from), to: toIso(draft.to) });
  }

  const rows = entries.data?.pages.flatMap((p) => p.data) ?? [];

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-h1 text-fg">{t('ops:audit.title')}</h1>
        <p className="mt-1 text-body-sm text-fg-secondary">{t('ops:audit.intro')}</p>
      </div>

      <Card>
        <form onSubmit={onSubmit} className="space-y-3">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {FIELDS.map((f) => (
              <div key={f.key} className="space-y-1">
                <label htmlFor={`audit-${f.key}`} className="block text-label text-fg-secondary">
                  {t(f.label)}
                </label>
                <Input
                  id={`audit-${f.key}`}
                  type={f.type ?? 'text'}
                  value={draft[f.key] ?? ''}
                  onChange={(e) => setDraft((d) => ({ ...d, [f.key]: e.target.value || undefined }))}
                />
              </div>
            ))}
          </div>
          <div className="flex gap-2">
            <Button type="submit" variant="secondary">
              {t('ops:audit.apply')}
            </Button>
            <Button
              type="button"
              variant="tertiary"
              onClick={() => {
                setDraft(EMPTY);
                setApplied(EMPTY);
              }}
            >
              {t('ops:audit.clear')}
            </Button>
          </div>
        </form>
      </Card>

      {entries.isLoading ? (
        <PageLoader />
      ) : entries.isError ? (
        <ErrorState message={localizeError(entries.error, t)} onRetry={() => void entries.refetch()} />
      ) : rows.length === 0 ? (
        <EmptyState title={t('ops:audit.empty')} />
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-body-sm">
              <caption className="sr-only">{t('ops:audit.title')}</caption>
              <thead>
                <tr className="border-b border-line-strong text-fg-secondary">
                  <th scope="col" className="py-2 pr-3">{t('ops:audit.col.time')}</th>
                  <th scope="col" className="py-2 pr-3">{t('ops:audit.col.actor')}</th>
                  <th scope="col" className="py-2 pr-3">{t('ops:audit.col.action')}</th>
                  <th scope="col" className="py-2">{t('ops:audit.col.resource')}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.seq} className="border-b border-line align-top">
                    <td className="py-2 pr-3 text-fg-muted">{new Date(row.server_time).toLocaleString()}</td>
                    <td className="py-2 pr-3 text-fg">
                      {row.actor_role}
                      {row.actor_user_id && (
                        <span className="block fk-numeric text-fg-muted">{row.actor_user_id.slice(-8)}</span>
                      )}
                    </td>
                    <td className="py-2 pr-3 font-semibold text-fg">{row.action}</td>
                    <td className="py-2 text-fg">
                      {row.entity_type}
                      {row.entity_id && <span className="block fk-numeric text-fg-muted">{row.entity_id}</span>}
                      {(row.before != null || row.after != null) && (
                        <details className="mt-1">
                          <summary className="cursor-pointer text-action-secondary-text">{t('ops:audit.details')}</summary>
                          <pre className="mt-1 max-w-md overflow-x-auto whitespace-pre-wrap rounded-md bg-surface-sunken p-2 text-body-sm">
                            {JSON.stringify({ before: row.before, after: row.after }, null, 2)}
                          </pre>
                        </details>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {entries.hasNextPage && (
            <div className="flex justify-center">
              <Button
                variant="secondary"
                loading={entries.isFetchingNextPage}
                onClick={() => void entries.fetchNextPage()}
              >
                {t('ops:audit.loadMore')}
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
