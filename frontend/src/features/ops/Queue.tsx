import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { Card } from '@/components/Card';
import { StatusBadge, type BadgeTone } from '@/components/StatusBadge';

/** A triage queue card (P3 §18.1; reused by the Platform Admin Control
 * page, §19.1): heading, a live count, an optional "View all" link. */
export function Queue({
  title,
  count,
  more,
  viewAll,
  children,
}: {
  title: string;
  count: number;
  more: boolean;
  viewAll?: string;
  children: ReactNode;
}): JSX.Element {
  const { t } = useTranslation('ops');
  const headingId = `queue-${title.replace(/\W+/g, '-').toLowerCase()}`;
  return (
    <Card>
      <section aria-labelledby={headingId} className="space-y-3">
        <div className="flex items-baseline justify-between gap-2">
          <h2 id={headingId} className="text-h3 text-fg">
            {title}
          </h2>
          {viewAll && (
            <Link to={viewAll} className="text-body-sm text-action-secondary-text underline">
              {t('overview.viewAll')}
            </Link>
          )}
        </div>
        <p aria-live="polite" className="text-body-sm text-fg-muted">
          {more ? t('overview.countMore', { count }) : t('overview.count', { count })}
        </p>
        <ul className="space-y-2">{children}</ul>
      </section>
    </Card>
  );
}

export function QueueRow({
  to,
  title,
  meta,
  badge,
  reason,
}: {
  to: string;
  title: string;
  meta: string;
  badge?: string;
  /** why the row is in the queue (F-15), e.g. "Under dispute" */
  reason?: { label: string; tone: BadgeTone };
}): JSX.Element {
  return (
    <li>
      <Link to={to} className="block rounded-md border border-line px-3 py-2 hover:bg-surface-sunken">
        <span className="flex flex-wrap items-center gap-2">
          <span className="fk-numeric text-body font-semibold text-fg">{title}</span>
          {reason && <StatusBadge tone={reason.tone} label={reason.label} />}
          {badge && <StatusBadge tone="warning" icon="lock" label={badge} />}
        </span>
        <span className="block text-body-sm text-fg-muted">{meta}</span>
      </Link>
    </li>
  );
}
