import type { ReactNode } from 'react';

import { JobStatusChip } from './JobStatusChip';
import { cn } from './cn';
import type { JobState } from '@/design/tokens';

/**
 * JobStatusHeader — Design Phase 4 §12/§30.3. The top of every Job detail:
 * the state chip + a plain-language line + an optional "as of HH:MM" cached badge.
 * Presentational: all copy is passed in.
 */
export function JobStatusHeader({
  state,
  stateLabel,
  line,
  asOf,
  className,
  children,
}: {
  state: JobState;
  stateLabel?: string;
  /** one plain-language sentence about what's happening */
  line: ReactNode;
  /** e.g. "14:20" — shown as "as of 14:20" when the view is from cache */
  asOf?: string;
  className?: string;
  children?: ReactNode;
}): JSX.Element {
  return (
    <header className={cn('space-y-1', className)}>
      <div className="flex flex-wrap items-center gap-2">
        <JobStatusChip state={state} label={stateLabel} />
        {asOf && <span className="fk-numeric text-caption text-fg-muted">· as of {asOf}</span>}
      </div>
      <p role="status" className="text-body text-fg">
        {line}
      </p>
      {children}
    </header>
  );
}
