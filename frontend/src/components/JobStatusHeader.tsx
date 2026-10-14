import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import { JobStatusChip } from './JobStatusChip';
import { cn } from './cn';
import type { JobState } from '@/design/tokens';

/**
 * JobStatusHeader — Design Phase 4 §12/§30.3. The top of every Job detail:
 * the state chip + a plain-language line + an optional "as of HH:MM" cached badge.
 * Presentational: the copy is passed in, apart from the "as of" wording.
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
  const { t } = useTranslation('common');
  return (
    <header className={cn('space-y-1', className)}>
      <div className="flex flex-wrap items-center gap-2">
        <JobStatusChip state={state} label={stateLabel} />
        {asOf && <span className="fk-numeric text-caption text-fg-muted">· {t('status.asOf', { time: asOf })}</span>}
      </div>
      <p role="status" className="text-body text-fg">
        {line}
      </p>
      {children}
    </header>
  );
}
