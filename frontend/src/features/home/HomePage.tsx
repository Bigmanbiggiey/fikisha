import { useTranslation } from 'react-i18next';

import { Alert } from '@/components/Alert';
import { Card } from '@/components/Card';
import { PageLoader } from '@/components/PageLoader';
import { StatusBadge } from '@/components/StatusBadge';
import { useAuth } from '@/features/auth/useAuth';
import { BusinessHomePage } from '@/features/jobs/BusinessHomePage';
import { OperatorHomePage } from '@/features/jobs/OperatorHomePage';
import { useWorkspaces } from '@/shell/useWorkspaces';

/**
 * `/home` is one route for every workspace (`design-phase-6-jobs-frontend-
 * plan.md` §3.1) — it dispatches on which workspace(s) the signed-in user
 * actually holds rather than being six separate home routes. Business
 * (Increment 2) and Operator (Increment 4) exist; everyone else still sees
 * the Phase 2A placeholder below until their workspace's Home is built. A
 * person with both a Business and an Operator workspace sees Business —
 * same documented simplification as `useActiveBusiness`'s "first workspace
 * of its kind" rule.
 */
export function HomePage(): JSX.Element {
  const { loading, workspaces } = useWorkspaces();
  if (loading) return <PageLoader />;
  if (workspaces.some((w) => w.kind === 'BUSINESS')) return <BusinessHomePage />;
  if (workspaces.some((w) => w.kind === 'OPERATOR')) return <OperatorHomePage />;
  return <GenericHomePlaceholder />;
}

function GenericHomePlaceholder(): JSX.Element {
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
