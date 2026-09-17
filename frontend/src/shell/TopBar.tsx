import { useTranslation } from 'react-i18next';
import { Link, NavLink, useNavigate } from 'react-router-dom';

import { Button } from '@/components/Button';
import { ConnectivityIndicator } from '@/components/ConnectivityIndicator';
import { cn } from '@/components/cn';
import { useAuth } from '@/features/auth/useAuth';
import { useOnline } from '@/design/useOnline';

import { LanguageSwitcher } from './LanguageSwitcher';

/**
 * TopBar — Design Phase 5B retone. IA / links unchanged from Phase 2A. The
 * language switcher and the connectivity indicator sit on the right, per
 * Phase 4 §10.3.
 */
export function TopBar(): JSX.Element {
  const { t } = useTranslation(['common', 'org']);
  const { status, logout } = useAuth();
  const online = useOnline();
  const navigate = useNavigate();

  const linkClass = ({ isActive }: { isActive: boolean }): string =>
    cn(
      'rounded-md px-2 py-1 text-label',
      isActive
        ? 'bg-surface-brand-tint text-action-primary-hover'
        : 'text-fg-secondary hover:text-fg',
    );

  return (
    <header className="border-b border-line bg-surface-nav">
      <div className="mx-auto flex max-w-3xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
        <Link to="/" className="text-h3 font-bold text-action-primary">
          {t('common:appName')}
        </Link>

        {status === 'authenticated' && (
          <nav className="flex flex-wrap items-center gap-1" aria-label={t('common:appName')}>
            <NavLink to="/home" className={linkClass}>
              {t('common:nav.home')}
            </NavLink>
            <NavLink to="/jobs" className={linkClass}>
              {t('common:nav.jobs')}
            </NavLink>
            <NavLink to="/businesses" className={linkClass}>
              {t('org:nav.businesses')}
            </NavLink>
            <NavLink to="/operator" className={linkClass}>
              {t('org:nav.operator')}
            </NavLink>
            <NavLink to="/groups" className={linkClass}>
              {t('org:nav.groups')}
            </NavLink>
            <NavLink to="/vehicles" className={linkClass}>
              {t('org:nav.vehicles')}
            </NavLink>
            <NavLink to="/verification" className={linkClass}>
              {t('org:nav.verification')}
            </NavLink>
            <NavLink to="/operating-locations" className={linkClass}>
              {t('org:nav.locations')}
            </NavLink>
            <NavLink to="/diagnostics" className={linkClass}>
              {t('common:nav.diagnostics')}
            </NavLink>
          </nav>
        )}

        <div className="ml-auto flex items-center gap-3">
          <ConnectivityIndicator state={online ? 'online' : 'offline'} />
          <LanguageSwitcher />
          {status === 'authenticated' && (
            <Button variant="tertiary" size="compact" onClick={() => void logout()}>
              {t('common:nav.signOut')}
            </Button>
          )}
          {status === 'anonymous' && (
            <Button variant="secondary" size="compact" onClick={() => navigate('/login')}>
              {t('common:nav.signIn')}
            </Button>
          )}
        </div>
      </div>
    </header>
  );
}
