import type { ReactNode } from 'react';

/**
 * EmptyState — Design Phase 5B. What is empty + why + the one relevant action.
 * Never "No data."
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
  return (
    <div className="rounded-md border border-dashed border-line-strong bg-surface-card p-8 text-center">
      <p className="text-h3 text-fg">{title}</p>
      {description && <p className="mt-1 text-body-sm text-fg-secondary">{description}</p>}
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  );
}
