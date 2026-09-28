import { useTranslation } from 'react-i18next';
import { Link, useLocation } from 'react-router-dom';

import { cn } from '@/components/cn';
import { Icon } from '@/design/Icon';

import { useActiveRole } from './activeRole';
import { isNavItemActive, navFor, type NavItem } from './navConfig';

const MORE: NavItem = { to: '/more', labelKey: 'common:nav.more', icon: 'menu', end: true };

/**
 * Bottom tab bar for phones (Design Phase 7 P-04; P3 §24.2): the active
 * role's primary items, its main action (Business "Request transport") and
 * More. Fixed to the bottom above the safe-area inset, 56 px targets.
 * Hidden from `md` up, where the top bar (tablet) or sidebar (desktop)
 * takes over.
 */
export function RoleTabBar(): JSX.Element | null {
  const { t } = useTranslation(['common', 'org']);
  const { pathname } = useLocation();
  const { loading, role } = useActiveRole();
  if (loading) return null;

  const nav = navFor(role);
  const items = [...nav.primary, ...(nav.action ? [nav.action] : []), MORE];
  // "More" also covers the secondary screens it links to.
  const moreActive = pathname === '/more' || nav.secondary.some((s) => isNavItemActive(s, pathname));

  return (
    <nav
      aria-label={t('common:nav.main')}
      className="fixed inset-x-0 bottom-0 z-nav border-t border-line bg-surface-nav pb-[env(safe-area-inset-bottom)] md:hidden"
    >
      <ul className="grid" style={{ gridTemplateColumns: `repeat(${items.length}, minmax(0, 1fr))` }}>
        {items.map((item) => {
          const active = item === MORE ? moreActive : isNavItemActive(item, pathname);
          return (
            <li key={item.to}>
              <Link
                to={item.to}
                aria-current={active ? 'page' : undefined}
                className={cn(
                  'flex min-h-target-driver flex-col items-center justify-center gap-0.5 px-1 py-1 text-center text-caption leading-tight',
                  active ? 'font-semibold text-action-primary' : 'text-fg-secondary',
                )}
              >
                <Icon name={item.icon} size={22} />
                <span>{t(item.labelKey)}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
