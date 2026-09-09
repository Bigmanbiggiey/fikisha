import { useTranslation } from 'react-i18next';
import { NavLink } from 'react-router-dom';

import { Button } from '@/components/Button';
import { cn } from '@/components/cn';
import { useAuth } from '@/features/auth/useAuth';

import { LanguageSwitcher } from './LanguageSwitcher';

export function TopBar(): JSX.Element {
  const { t } = useTranslation(['common', 'org']);
  const { status, logout } = useAuth();

  const linkClass = ({ isActive }: { isActive: boolean }): string =>
    cn(
      'rounded-md px-2 py-1 text-sm font-medium',
      isActive ? 'bg-brand-50 text-brand-800' : 'text-slate-600 hover:text-slate-900',
    );

  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-3xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
        <span className="text-base font-semibold text-brand-700">{t('common:appName')}</span>

        {status === 'authenticated' && (
          <nav className="flex flex-wrap items-center gap-1">
            <NavLink to="/" end className={linkClass}>
              {t('common:nav.home')}
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
          <LanguageSwitcher />
          {status === 'authenticated' && (
            <Button variant="ghost" onClick={() => void logout()}>
              {t('common:nav.signOut')}
            </Button>
          )}
        </div>
      </div>
    </header>
  );
}
