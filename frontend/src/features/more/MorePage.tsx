import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { Icon } from '@/design/Icon';
import { useAuth } from '@/features/auth/useAuth';
import { useActiveRole } from '@/shell/activeRole';
import { LanguageSwitcher } from '@/shell/LanguageSwitcher';
import { NAV } from '@/shell/navConfig';
import { RoleSwitch } from '@/shell/RoleSwitch';

/**
 * More (Design Phase 7 P-04; P1 §5–§8 "More"): the active role's secondary
 * screens, the role switch for people with more than one role, language,
 * and sign out. The phone tab bar's last item; also reachable on desktop.
 */
export function MorePage(): JSX.Element {
  const { t } = useTranslation(['common', 'org']);
  const { logout } = useAuth();
  const { role } = useActiveRole();
  const secondary = role ? NAV[role].secondary : [];

  return (
    <div className="space-y-5">
      <h1 className="text-h1 text-fg">{t('common:nav.more')}</h1>

      {secondary.length > 0 && (
        <div className="rounded-md border border-line bg-surface-card">
          <ul className="divide-y divide-line">
            {secondary.map((item) => (
              <li key={item.to}>
                <Link to={item.to} className="flex min-h-target-driver items-center gap-3 px-4 text-body text-fg">
                  <Icon name={item.icon} size={22} className="text-fg-secondary" />
                  <span className="flex-1">{t(item.labelKey)}</span>
                  <Icon name="chevronRight" size={20} className="text-fg-muted" />
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}

      <RoleSwitch />

      <Card>
        <h2 className="text-label text-fg-secondary">{t('common:language.label')}</h2>
        <div className="mt-2">
          <LanguageSwitcher />
        </div>
      </Card>

      <Button variant="secondary" fullWidth onClick={() => void logout()}>
        {t('common:nav.signOut')}
      </Button>
    </div>
  );
}
