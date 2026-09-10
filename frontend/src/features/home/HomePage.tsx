import { useTranslation } from 'react-i18next';

import { Alert } from '@/components/Alert';
import { Card } from '@/components/Card';
import { StatusBadge } from '@/components/StatusBadge';
import { useAuth } from '@/features/auth/useAuth';

export function HomePage(): JSX.Element {
  const { t } = useTranslation('common');
  const { user } = useAuth();
  if (!user) return <></>;

  const displayName = user.display_name || user.phone;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-h1 text-fg">{t('home.welcome', { name: displayName })}</h1>
        <p className="mt-1 text-body-sm text-fg-muted">
          {t('home.signedInAs', { phone: user.phone })}
        </p>
      </div>

      <Alert tone="info">{t('home.foundationNote')}</Alert>

      <Card>
        <h2 className="text-label text-fg-secondary">{t('home.roles')}</h2>
        <div className="mt-2 flex flex-wrap gap-2">
          {user.roles.length > 0 ? (
            user.roles.map((role) => <StatusBadge key={role} tone="brand" label={role} />)
          ) : (
            <span className="text-body-sm text-fg-muted">{t('home.noRoles')}</span>
          )}
        </div>
      </Card>
    </div>
  );
}
