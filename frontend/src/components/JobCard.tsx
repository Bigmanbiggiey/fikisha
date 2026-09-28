import { Card } from './Card';
import { Icon, type IconName } from '@/design/Icon';
import { JobStatusChip } from './JobStatusChip';
import type { JobState } from '@/design/tokens';

/**
 * JobCard — Design Phase 4 §12/§30.5. A list/grid item for one Job. The whole
 * card is the tap target (pass `href` via the parent link or `onClick`).
 * Presentational — the caller supplies already-formatted strings.
 *
 * The reference and the state chip share the top row and the chip never
 * shrinks, so the state stays readable at 360px (Design Phase 7 F-01; the
 * route used to share a row with the chip and squeeze it). The accessible
 * name includes the state: `aria-label` replaces the card's content, so
 * without it a screen reader never announced the status.
 */
export function JobCard({
  reference,
  state,
  stateLabel,
  route,
  cargo,
  meta,
  vehicleIcon = 'truck',
  price,
  nextActionHint,
  onClick,
  className,
}: {
  reference: string;
  state: JobState;
  stateLabel?: string;
  route: { from: string; to: string };
  cargo: string;
  meta?: string;
  vehicleIcon?: IconName;
  price?: string;
  nextActionHint?: string;
  onClick?: () => void;
  className?: string;
}): JSX.Element {
  const interactive = Boolean(onClick);
  return (
    <Card
      interactive={interactive}
      onClick={onClick}
      role={interactive ? 'button' : undefined}
      tabIndex={interactive ? 0 : undefined}
      onKeyDown={
        interactive
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick?.();
              }
            }
          : undefined
      }
      aria-label={
        interactive ? `Job ${reference}, ${stateLabel ?? state}, ${route.from} to ${route.to}` : undefined
      }
      className={className}
    >
      <div className="flex items-center justify-between gap-2">
        <p className="fk-numeric text-caption text-fg-muted">{reference}</p>
        <JobStatusChip state={state} label={stateLabel} />
      </div>
      <p className="mt-1 text-h3 text-fg">
        {route.from} <span className="text-fg-muted">→</span> {route.to}
      </p>
      <p className="mt-1 text-body text-fg">{cargo}</p>
      {meta && <p className="text-body-sm text-fg-secondary">{meta}</p>}
      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-body-sm text-fg-secondary">
        <span className="inline-flex items-center gap-1">
          <Icon name={vehicleIcon} size={16} />
        </span>
        {price && <span className="fk-numeric text-fg">{price}</span>}
      </div>
      {nextActionHint && (
        <p className="mt-2 inline-flex items-center gap-1 text-body-sm text-action-secondary-text">
          {nextActionHint}
          <Icon name="chevronRight" size={14} />
        </p>
      )}
    </Card>
  );
}
