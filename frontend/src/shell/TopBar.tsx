import { useTranslation } from 'react-i18next';
import { Link, useLocation, useNavigate } from 'react-router-dom';

import { Button } from '@/components/Button';
import { ConnectivityIndicator } from '@/components/ConnectivityIndicator';
import { cn } from '@/components/cn';
import { useAuth } from '@/features/auth/useAuth';
import { useOnline } from '@/design/useOnline';

import { useActiveRole } from './activeRole';
import { LanguageSwitcher } from './LanguageSwitcher';
import { isNavItemActive, navFor, type NavItem } from './navConfig';

/**
 * TopBar (Design Phase 7 P-04). No longer lists every link: navigation
 * lives in the role tab bar (phones) and sidebar (desktop). What stays is
 * the wordmark, connectivity and language on every width, plus:
 * - tablets (`md` up to `lg`): the active role's items inline, with More,
 *   since neither the tab bar nor the sidebar shows there;
 * - from `md`: Sign out (on phones it lives in More).
 * The inner container matches the page body's width, so the header lines
 * up with the content on every route, including `/ops`.
 */
export function TopBar(): JSX.Element {
  const { t } = useTranslation(['common', 'org']);
  const { status, logout } = useAuth();
  const online = useOnline();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { loading, role } = useActiveRole();

  const nav = status === 'authenticated' && !loading ? navFor(role) : null;
  const inline: NavItem[] = nav
    ? [
        ...nav.primary,
        ...(nav.action ? [nav.action] : []),
        { to: '/more', labelKey: 'common:nav.more', icon: 'menu', end: true },
      ]
    : [];

  return (
    <header className="border-b border-line bg-surface-nav">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
        <Link to="/" className="text-h3 font-bold text-action-primary">
          {t('common:appName')}
        </Link>

        {inline.length > 0 && (
          <nav aria-label={t('common:nav.main')} className="hidden items-center gap-1 md:flex lg:hidden">
            {inline.map((item) => {
              const active = isNavItemActive(item, pathname);
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  aria-current={active ? 'page' : undefined}
                  className={cn(
                    'flex min-h-target items-center rounded-md px-2 text-label',
                    active ? 'bg-surface-brand-tint text-action-primary-hover' : 'text-fg-secondary hover:text-fg',
                  )}
                >
                  {t(item.labelKey)}
                </Link>
              );
            })}
          </nav>
        )}

        <div className="ml-auto flex items-center gap-3">
          <ConnectivityIndicator state={online ? 'online' : 'offline'} />
          <LanguageSwitcher />
          {status === 'authenticated' && (
            <span className="hidden md:inline-flex">
              <Button variant="tertiary" onClick={() => void logout()}>
                {t('common:nav.signOut')}
              </Button>
            </span>
          )}
          {status === 'anonymous' && (
            <Button variant="secondary" onClick={() => navigate('/login')}>
              {t('common:nav.signIn')}
            </Button>
          )}
        </div>
      </div>
    </header>
  );
}
