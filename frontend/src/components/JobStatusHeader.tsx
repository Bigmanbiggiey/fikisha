import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import { JobStatusChip } from './JobStatusChip';
import { cn } from './cn';
import type { JobState } from '@/design/tokens';

/**
 * JobStatusHeader — Design Phase 4 §12/§30.3, Design Phase 7 P-08. The top
 * of every Job detail and the page's one `<h1>`: the job reference, the
 * state chip with an optional "as of HH:MM" cached badge, an optional route
 * summary, a plain-language line, and an optional extra row (the staff
 * variant's business, band and review note). The caller passes the copy,
 * apart from the "Job …" and "as of" wording.
 */
export function JobStatusHeader({
  reference,
  state,
  stateLabel,
  route,
  line,
  asOf,
  extra,
  className,
  children,
}: {
  /** the short job reference, e.g. "7F3A2C"; rendered as the page's h1 */
  reference?: string;
  state: JobState;
  stateLabel?: string;
  /** "Pickup → Destination", when known */
  route?: { from: string; to: string };
  /** one plain-language sentence about what's happening */
  line: ReactNode;
  /** e.g. "14:20" — shown as "as of 14:20" when the view is from cache */
  asOf?: string;
  /** an extra row under the chip (e.g. staff context) */
  extra?: ReactNode;
  className?: string;
  children?: ReactNode;
}): JSX.Element {
  const { t } = useTranslation('common');
  return (
    <header className={cn('space-y-1', className)}>
      {reference && <h1 className="fk-numeric text-h1 text-fg">{t('job.title', { ref: reference })}</h1>}
      <div className="flex flex-wrap items-center gap-2">
        <JobStatusChip state={state} label={stateLabel} />
        {asOf && <span className="fk-numeric text-caption text-fg-muted">· {t('status.asOf', { time: asOf })}</span>}
      </div>
      {route && (route.from || route.to) && (
        <p className="text-body-sm text-fg-secondary">
          {route.from || '—'} → {route.to || '—'}
        </p>
      )}
      {extra}
      <p role="status" className="text-body text-fg">
        {line}
      </p>
      {children}
    </header>
  );
}
