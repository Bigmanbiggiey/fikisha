import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Card } from '@/components/Card';
import { StatusBadge, type BadgeTone } from '@/components/StatusBadge';
import { Icon } from '@/design/Icon';
import { formatKes } from '@/features/jobs/money';
import { formatDateTime } from '@/services/datetime';

import type { TierChange, TierCriterion, TierLevel, TierView } from './types';

const TONE: Record<TierLevel, BadgeTone> = {
  L0: 'neutral',
  L1: 'info',
  L2: 'brand',
  L3: 'success',
  RESTRICTED: 'warning',
};

export function TierBadge({ level }: { level: TierLevel }): JSX.Element {
  const { t } = useTranslation('trust');
  return <StatusBadge tone={TONE[level]} label={t(`trust:level.${level}`)} />;
}

function allowedLine(view: TierView, t: (k: string, o?: Record<string, unknown>) => string): string {
  if (view.level === 'L0') return t('trust:allowed.none');
  if (view.max_value_kes === null) return t('trust:allowed.noCap');
  return t('trust:allowed.upTo', { amount: formatKes(view.max_value_kes) });
}

/** Rows that show a figure only once measured have a plain label otherwise. */
function labelKey(c: TierCriterion): string {
  if (c.status === 'NOT_MEASURED') return `${c.key}_unmeasured`;
  if (c.status === 'INSUFFICIENT_DATA') return `${c.key}_insufficient`;
  return c.key;
}

function CriterionRow({ c }: { c: TierCriterion }): JSX.Element {
  const { t } = useTranslation('trust');
  const icon = c.status === 'MET' ? 'check' : c.status === 'NOT_MEASURED' ? 'slash' : 'circle';
  const tone =
    c.status === 'MET' ? 'text-status-success-fg' : c.status === 'NOT_MEASURED' ? 'text-fg-muted' : 'text-fg-secondary';
  return (
    <li className="flex items-start gap-2 text-body-sm">
      <span className={tone}>
        <Icon name={icon} />
      </span>
      <span className={c.status === 'NOT_MEASURED' ? 'text-fg-muted' : 'text-fg'}>
        {t(`trust:criterion.${labelKey(c)}`, {
          current: c.current ?? 0,
          target: c.target ?? 0,
          defaultValue: t(`trust:criterion.${c.key}`, {
            current: c.current ?? 0,
            target: c.target ?? 0,
            defaultValue: c.key,
          }),
        })}
        {c.status === 'NOT_MEASURED' && ` · ${t('trust:notMeasured')}`}
        {c.status === 'INSUFFICIENT_DATA' && ` · ${t('trust:insufficient', { current: c.current ?? 0 })}`}
        <span className="sr-only"> · {t(`trust:status.${c.status}`)}</span>
      </span>
    </li>
  );
}

export function TierHistory({ history, staff = false }: { history: TierChange[]; staff?: boolean }): JSX.Element {
  const { t } = useTranslation('trust');
  if (history.length === 0) return <p className="text-body-sm text-fg-muted">{t('trust:history.none')}</p>;
  return (
    <ul className="space-y-3">
      {history.map((h) => (
        <li key={h.id} className="text-body-sm">
          <span className="font-semibold text-fg">
            {t(`trust:level.${h.from_level}`)} → {t(`trust:level.${h.to_level}`)} · {t(`trust:trigger.${h.trigger}`)}
          </span>
          {h.reason && <span className="block text-fg-secondary">{h.reason}</span>}
          <span className="block text-fg-muted">
            {[formatDateTime(h.created_at), staff ? h.by : null].filter(Boolean).join(' · ')}
          </span>
        </li>
      ))}
    </ul>
  );
}

/**
 * An operator's tier (operator-tiers plan T-3): the tier, the job values it
 * allows, the checklist toward the next tier, and the history. `compact`
 * (operator Home) shows the tier and a link to the full card. `staff`
 * words it for Fikisha staff and shows who made each change.
 */
export function TierCard({
  view,
  compact = false,
  staff = false,
}: {
  view: TierView;
  compact?: boolean;
  staff?: boolean;
}): JSX.Element {
  const { t } = useTranslation('trust');
  const who = staff ? 'staff' : 'self';
  const pending = view.open_proposal !== null;
  return (
    <Card className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-h3 text-fg">{t(`trust:title.${who}`)}</h2>
        <TierBadge level={view.level} />
      </div>
      <p className="text-body text-fg">{allowedLine(view, t)}</p>
      {view.level === 'RESTRICTED' && <Alert tone="warning">{t(`trust:restricted.${who}`)}</Alert>}
      {view.level === 'L0' && view.stored_level !== 'L1' && (
        <Alert tone="warning">{t(`trust:lapsed.${who}`, { level: t(`trust:level.${view.stored_level}`) })}</Alert>
      )}

      {compact ? (
        <Link to="/operator" className="inline-block text-body-sm font-medium text-action-secondary-text underline">
          {view.next_level ? t('trust:seeProgress', { level: t(`trust:level.${view.next_level}`) }) : t('trust:seeTier')}
        </Link>
      ) : (
        <>
          {view.next_level && (
            <div className="space-y-2">
              <h3 className="text-label text-fg-secondary">
                {t('trust:toward', { level: t(`trust:level.${view.next_level}`) })}
              </h3>
              <ul className="space-y-1">
                {view.criteria.map((c) => (
                  <CriterionRow key={c.key} c={c} />
                ))}
              </ul>
              {(view.ready_for_review || pending) && (
                <Alert tone="info">
                  {t(`trust:${pending ? 'proposed' : 'ready'}.${who}`, { level: t(`trust:level.${view.next_level}`) })}
                </Alert>
              )}
              {view.next_level !== 'L1' && <p className="text-body-sm text-fg-muted">{t(`trust:howItWorks.${who}`)}</p>}
            </div>
          )}
          <div className="space-y-2">
            <h3 className="text-label text-fg-secondary">{t('trust:history.title')}</h3>
            <TierHistory history={view.history} staff={staff} />
          </div>
        </>
      )}
    </Card>
  );
}
