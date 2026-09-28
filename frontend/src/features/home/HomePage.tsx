import { useTranslation } from 'react-i18next';
import { Navigate } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Card } from '@/components/Card';
import { PageLoader } from '@/components/PageLoader';
import { StatusBadge } from '@/components/StatusBadge';
import { useAuth } from '@/features/auth/useAuth';
import { BusinessHomePage } from '@/features/jobs/BusinessHomePage';
import { OperatorHomePage } from '@/features/jobs/OperatorHomePage';
import { OpsHomePage } from '@/features/ops/OpsHomePage';
import { useActiveRole } from '@/shell/activeRole';
import { useWorkspaces } from '@/shell/useWorkspaces';

/**
 * `/home` is one route for every workspace (`design-phase-6-jobs-frontend-
 * plan.md` §3.1). It shows the Home of the **active navigation role**
 * (Design Phase 7 P-04; the person picks it with the role switch, default
 * Business → Operator → Driver → Group Manager → staff). A driver's home is
 * Current job; a group manager sees the operator Home (their own operator
 * profile's work) until a group Home exists; staff land on the Ops overview.
 * Someone with no role yet sees the placeholder below.
 */
export function HomePage(): JSX.Element {
  const { loading: workspacesLoading, workspaces } = useWorkspaces();
  const { loading, role } = useActiveRole();
  if (loading || workspacesLoading) return <PageLoader />;
  switch (role) {
    case 'BUSINESS':
      return <BusinessHomePage />;
    case 'OPERATOR':
      return <OperatorHomePage />;
    case 'DRIVER':
      return <Navigate to="/current-job" replace />;
    case 'GROUP_MANAGER':
      return workspaces.some((w) => w.kind === 'OPERATOR') ? <OperatorHomePage /> : <GenericHomePlaceholder />;
    case 'OPERATIONS_OFFICER':
    case 'PLATFORM_ADMIN':
      return <OpsHomePage />;
    default:
      return <GenericHomePlaceholder />;
  }
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
