import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Card } from '@/components/Card';
import { PageLoader } from '@/components/PageLoader';
import { VerificationPill } from '@/components/VerificationPill';
import { Icon } from '@/design/Icon';
import type { VerificationState } from '@/design/tokens';
import { vehiclesApi } from '@/features/vehicles/vehiclesApi';
import { verificationApi } from '@/features/verification/verificationApi';
import { useAuth } from '@/features/auth/useAuth';

/**
 * Home for an operator Fikisha has not approved yet (assessment 2026-10-19
 * D-2): what they still need to do, and that a Fikisha reviewer approves
 * them. Work, jobs and messages open once they are approved.
 */
export function PendingOperatorHome({ operatorId }: { operatorId: string }): JSX.Element {
  const { t } = useTranslation('org');
  const { user } = useAuth();
  const status = useQuery({
    queryKey: ['verification-status', 'OPERATOR', operatorId],
    queryFn: () => verificationApi.subjectStatus('OPERATOR', operatorId),
    retry: false,
  });
  const vehicles = useQuery({
    queryKey: ['vehicles', user?.id],
    queryFn: vehiclesApi.list,
    retry: false,
  });
  if (status.isLoading || vehicles.isLoading) return <PageLoader />;

  const required = (status.data?.requirements ?? []).filter((r) => r.mandatory);
  const hasVehicle = (vehicles.data?.data ?? []).some((v) => v.owner_operator_id === operatorId);

  return (
    <div className="space-y-5">
      <h1 className="text-h1 text-fg">{t('operatorApproval.title')}</h1>
      <Alert tone="info" title={t('operatorApproval.waitingTitle')}>
        {t('operatorApproval.waitingBody')}
      </Alert>
      <Card>
        <h2 className="text-label text-fg-secondary">{t('operatorApproval.checklist')}</h2>
        <ul className="mt-3 divide-y divide-line text-body-sm">
          <ChecklistRow done label={t('operatorApproval.profile')} to="/operator" />
          {required.map((r) => (
            <li key={r.domain} className="flex items-center justify-between gap-2 py-2">
              <Link to="/operator" className="font-medium text-fg underline-offset-2 hover:underline">
                {t(`operatorApproval.domain.${r.domain}`, { defaultValue: r.domain })}
              </Link>
              <VerificationPill state={r.state as VerificationState} hideDomain />
            </li>
          ))}
          <ChecklistRow done={hasVehicle} label={t('operatorApproval.vehicle')} to="/vehicles" />
          <li className="flex items-center gap-2 py-2 text-fg-secondary">
            <Icon name="circle" size={18} />
            <span>{t('operatorApproval.review')}</span>
          </li>
        </ul>
      </Card>
    </div>
  );
}

function ChecklistRow({ done, label, to }: { done: boolean; label: string; to: string }): JSX.Element {
  const { t } = useTranslation('org');
  return (
    <li className="flex items-center justify-between gap-2 py-2">
      <Link to={to} className="font-medium text-fg underline-offset-2 hover:underline">
        {label}
      </Link>
      <span className={done ? 'flex items-center gap-1 text-status-success-fg' : 'flex items-center gap-1 text-fg-muted'}>
        <Icon name={done ? 'check' : 'circle'} size={18} />
        {done ? t('operatorApproval.done') : t('operatorApproval.todo')}
      </span>
    </li>
  );
}
