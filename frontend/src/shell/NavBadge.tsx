import { useTranslation } from 'react-i18next';

import { cn } from '@/components/cn';

/** Unread count on a navigation item (Messages, 10g). Hidden at zero; the
 * number is shown, and "3 unread" is read out. */
export function NavBadge({ count, className }: { count: number; className?: string }): JSX.Element | null {
  const { t } = useTranslation('common');
  if (count <= 0) return null;
  return (
    <span
      className={cn(
        'inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-action-primary px-1.5 text-caption font-semibold leading-none text-action-on-primary',
        className,
      )}
    >
      <span aria-hidden>{count > 99 ? '99+' : count}</span>
      <span className="sr-only">{t('common:nav.unreadBadge', { count })}</span>
    </span>
  );
}
