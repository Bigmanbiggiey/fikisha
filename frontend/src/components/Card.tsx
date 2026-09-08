import type { ReactNode } from 'react';

import { cn } from './cn';

export function Card({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}): JSX.Element {
  return (
    <div
      className={cn(
        'rounded-xl border border-slate-200 bg-white p-5 shadow-sm',
        className,
      )}
    >
      {children}
    </div>
  );
}
