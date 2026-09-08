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
        <h1 className="text-xl font-semibold text-slate-900">
          {t('home.welcome', { name: displayName })}
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          {t('home.signedInAs', { phone: user.phone })}
        </p>
      </div>

      <Alert tone="info">{t('home.foundationNote')}</Alert>

      <Card>
        <h2 className="text-sm font-medium text-slate-700">{t('home.roles')}</h2>
        <div className="mt-2 flex flex-wrap gap-2">
          {user.roles.length > 0 ? (
            user.roles.map((role) => <StatusBadge key={role} label={role} />)
          ) : (
            <span className="text-sm text-slate-500">{t('home.noRoles')}</span>
          )}
        </div>
      </Card>
    </div>
  );
}
