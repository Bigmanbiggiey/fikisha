import type { ReactNode } from 'react';

import { Icon } from '@/design/Icon';
import { cn } from './cn';

export type TimelineNode = 'done' | 'current' | 'upcoming' | 'pending-sync';
export type TimelineEndCap = 'cancelled' | 'failed' | 'disputed';

export interface TimelineStep {
  id: string;
  label: ReactNode;
  node: TimelineNode;
  time?: string;
  actor?: string;
  /** e.g. "OTP", "Photo", "Signature" */
  proof?: string;
  /** e.g. "Verified pickup" / "Operator-attested — unverified" */
  marker?: { text: string; tone: 'success' | 'warning' };
  note?: ReactNode;
}

/**
 * JobTimeline — Design Phase 4 §14/§30.6. Human-readable progress as an ordered
 * list. Nodes carry a distinct shape (not colour alone): ✓ done, ● current,
 * ○ upcoming, dashed pending-sync. `endCap` renders the off-happy-path terminal
 * treatment (Cancelled / Couldn't complete / Under dispute).
 */
export function JobTimeline({
  steps,
  endCap,
  endCapText,
  className,
}: {
  steps: TimelineStep[];
  endCap?: TimelineEndCap;
  endCapText?: ReactNode;
  className?: string;
}): JSX.Element {
  return (
    <div className={className}>
      {endCap === 'disputed' && (
        <p
          role="status"
          className="mb-3 flex items-center gap-2 rounded-md border border-status-warning-border bg-status-warning-bg px-3 py-2 text-body-sm text-status-warning-fg"
        >
          <Icon name="pause" size={16} />
          {endCapText ?? 'Under dispute — normal steps are paused.'}
        </p>
      )}
      <ol className="space-y-3">
        {steps.map((s) => (
          <li key={s.id} className="flex gap-3" aria-current={s.node === 'current' ? 'step' : undefined}>
            <TimelineNodeGlyph node={s.node} />
            <div className="min-w-0">
              <p className={cn('text-body', s.node === 'current' ? 'font-semibold text-fg' : 'text-fg')}>
                {s.label}
                {s.time && <span className="ml-2 fk-numeric text-caption text-fg-muted">{s.time}</span>}
              </p>
              {(s.actor || s.proof || s.marker) && (
                <p className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-caption text-fg-secondary">
                  {s.actor && <span>{s.actor}</span>}
                  {s.proof && (
                    <span className="rounded-sm bg-surface-sunken px-1.5 py-px text-fg-secondary">
                      {s.proof}
                    </span>
                  )}
                  {s.marker && (
                    <span
                      className={cn(
                        'inline-flex items-center gap-1',
                        s.marker.tone === 'success'
                          ? 'text-status-success-fg'
                          : 'text-status-warning-fg',
                      )}
                    >
                      <Icon name={s.marker.tone === 'success' ? 'check' : 'alert'} size={13} />
                      {s.marker.text}
                    </span>
                  )}
                </p>
              )}
              {s.note && <p className="mt-0.5 text-body-sm text-fg-secondary">{s.note}</p>}
              {s.node === 'pending-sync' && (
                <p className="mt-0.5 text-caption text-fg-muted">recorded on this phone · syncing</p>
              )}
            </div>
          </li>
        ))}
      </ol>
      {endCap && endCap !== 'disputed' && (
        <div
          className={cn(
            'mt-3 flex items-center gap-2 rounded-md border px-3 py-2 text-body-sm',
            endCap === 'cancelled'
              ? 'border-line-strong text-status-neutral-fg'
              : 'border-status-danger-border text-status-danger-fg',
          )}
        >
          <Icon name={endCap === 'cancelled' ? 'slash' : 'alertTriangle'} size={16} />
          {endCapText ?? (endCap === 'cancelled' ? 'Cancelled' : "Couldn't complete")}
        </div>
      )}
    </div>
  );
}

function TimelineNodeGlyph({ node }: { node: TimelineNode }): JSX.Element {
  if (node === 'done') {
    return (
      <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-status-success-solid text-fg-inverse">
        <Icon name="check" size={12} />
      </span>
    );
  }
  if (node === 'current') {
    return (
      <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-action-primary text-fg-inverse">
        <Icon name="dot" size={10} />
      </span>
    );
  }
  if (node === 'pending-sync') {
    return (
      <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 border-dashed border-line-strong text-fg-muted" />
    );
  }
  return (
    <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 border-line-strong text-fg-muted" />
  );
}
