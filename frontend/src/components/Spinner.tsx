import { cn } from './cn';

export function Spinner({ className }: { className?: string }): JSX.Element {
  return (
    <span
      role="status"
      aria-live="polite"
      className={cn(
        'inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent',
        className,
      )}
    />
  );
}
