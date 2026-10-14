import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import { useOnline } from '@/design/useOnline';

/**
 * EmptyState — Design Phase 5B. What is empty + why + the one relevant action.
 * Never "No data."
 *
 * Offline (Increment 10f): a list that was never loaded is not empty, it
 * just couldn't load — a query started offline is paused, not failed, so the
 * page falls through to here with no data. Say that instead of claiming
 * there's nothing (P3 §22 Offline).
 */
export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}): JSX.Element {
  const { t } = useTranslation('common');
  const online = useOnline();
  if (!online) {
    return (
      <div role="status" className="rounded-md border border-dashed border-line-strong bg-surface-card p-8 text-center">
        <p className="text-h3 text-fg">{t('offline.emptyTitle')}</p>
        <p className="mt-1 text-body-sm text-fg-secondary">{t('offline.emptyBody')}</p>
      </div>
    );
  }
  return (
    <div className="rounded-md border border-dashed border-line-strong bg-surface-card p-8 text-center">
      <p className="text-h3 text-fg">{title}</p>
      {description && <p className="mt-1 text-body-sm text-fg-secondary">{description}</p>}
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  );
}
