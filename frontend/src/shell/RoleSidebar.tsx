import { useTranslation } from 'react-i18next';
import { Link, useLocation } from 'react-router-dom';

import { cn } from '@/components/cn';
import { Icon } from '@/design/Icon';

import { useUnreadMessages } from '@/features/messages/useUnreadMessages';

import { useActiveRole } from './activeRole';
import { NavBadge } from './NavBadge';
import { isNavItemActive, navFor, type NavItem } from './navConfig';
import { RoleSwitch } from './RoleSwitch';

/**
 * Persistent sidebar for desktop (Design Phase 7 P-04; P3 §24.2, IA §23):
 * the role's main action at the top (Business "Request transport"), its
 * primary items, a secondary group, and the role switch for people with
 * more than one role. Shown from `lg` up.
 */
export function RoleSidebar(): JSX.Element | null {
  const { t } = useTranslation(['common', 'org']);
  const { pathname } = useLocation();
  const { loading, role } = useActiveRole();
  const nav = navFor(role);
  const unread = useUnreadMessages(!loading && nav.primary.some((i) => i.badge === 'messages'));
  if (loading) return null;

  const link = (item: NavItem): JSX.Element => {
    const active = isNavItemActive(item, pathname);
    return (
      <li key={item.to}>
        <Link
          to={item.to}
          aria-current={active ? 'page' : undefined}
          className={cn(
            'flex min-h-target items-center gap-3 rounded-md px-3 text-body',
            active ? 'bg-surface-brand-tint font-semibold text-action-primary' : 'text-fg-secondary hover:text-fg',
          )}
        >
          <Icon name={item.icon} size={20} />
          <span className="flex-1">{t(item.labelKey)}</span>
          {item.badge === 'messages' && <NavBadge count={unread} />}
        </Link>
      </li>
    );
  };

  return (
    <aside className="hidden w-56 shrink-0 py-6 lg:block">
      <nav aria-label={t('common:nav.main')} className="sticky top-6 space-y-5">
        {nav.action && (
          <Link
            to={nav.action.to}
            className="flex min-h-target items-center justify-center gap-2 rounded-md bg-action-primary px-4 text-body font-semibold text-action-on-primary hover:bg-action-primary-hover"
          >
            <Icon name={nav.action.icon} size={20} />
            {t(nav.action.labelKey)}
          </Link>
        )}
        <ul className="space-y-1">{nav.primary.map(link)}</ul>
        {nav.secondary.length > 0 && (
          <div>
            <h2 className="px-3 pb-1 text-label text-fg-muted">{t('common:nav.more')}</h2>
            <ul className="space-y-1">{nav.secondary.map(link)}</ul>
          </div>
        )}
        <RoleSwitch />
      </nav>
    </aside>
  );
}
