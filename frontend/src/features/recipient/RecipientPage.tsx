import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { PageLoader } from '@/components/PageLoader';
import { RecipientHeader } from '@/components/RecipientHeader';
import { recipientApi } from '@/features/jobs/recipientApi';
import { ApiError } from '@/services/problem';

const STATUS_KEYS = new Set([
  'AT_PICKUP',
  'PICKED_UP',
  'IN_TRANSIT',
  'AT_DESTINATION',
  'DELIVERED',
  'COMPLETED',
  'CANCELLED',
  'FAILED',
  'DISPUTED',
]);

/**
 * RecipientPage — Design Phase 6 Increment 6, §20.1 "Scoped-link shell".
 * The recipient's entry point: no account, no `AppShell`/`TopBar` (the
 * route sits outside both `RequireAuth` and `AppShell` in `router.tsx`,
 * mirroring the one existing precedent — `/login`). The token in the URL
 * is the only credential; `recipientApi.view()` sends no bearer header.
 *
 * `status_label` from the API is a fixed-English backend string (plan
 * `_STATUS_LABELS = dict(JobStatus.choices)`) — not re-localized for SW,
 * so the status line is derived client-side from `status` via i18n instead
 * of rendered verbatim, keeping the EN|SW toggle meaningful.
 */
export function RecipientPage(): JSX.Element {
  const { token } = useParams<{ token: string }>();
  const { t } = useTranslation('recipient');

  const view = useQuery({
    queryKey: ['recipient', token],
    queryFn: () => recipientApi.view(token!),
    enabled: !!token,
    retry: false,
  });

  if (view.isLoading) return <PageLoader />;

  if (view.isError) {
    const code = view.error instanceof ApiError ? view.error.code : '';
    const message =
      code === 'recipient_link_inactive'
        ? t('shell.linkExpired')
        : t('shell.linkInvalid');
    return (
      <div className="min-h-full bg-surface-page">
        <RecipientHeader />
        <div className="mx-auto max-w-md space-y-4 px-4 py-6">
          <Alert tone="danger">{message}</Alert>
        </div>
      </div>
    );
  }

  const data = view.data!;
  const statusKey = STATUS_KEYS.has(data.status) ? data.status : 'DEFAULT';
  const isDelivered = data.status === 'DELIVERED' || data.status === 'COMPLETED';
  const isAtDestination = data.status === 'AT_DESTINATION';
  const canConfirm = isAtDestination && data.allowed_actions.includes('CONFIRM_RECEIPT');
  const canReport = isAtDestination && data.allowed_actions.includes('REPORT_ISSUE');

  return (
    <div className="min-h-full bg-surface-page">
      <RecipientHeader />
      <div className="mx-auto max-w-md space-y-4 px-4 py-6">
        <div>
          <h1 className="text-h1 text-fg">
            {t('shell.title', { name: data.recipient_display_name })}
          </h1>
          <p role="status" className="text-body text-fg-secondary">
            {t(`shell.status.${statusKey}`, { defaultValue: data.status_label })}
          </p>
        </div>

        <Card className="space-y-2">
          <p className="text-body-sm text-fg-secondary">
            {t('shell.coming', { summary: data.cargo_summary })}
          </p>
          {data.driver_first_name && (
            <p className="text-body-sm text-fg-secondary">
              {t('shell.driver', { name: data.driver_first_name })}
            </p>
          )}
          {(data.vehicle_class || data.vehicle_plate) && (
            <p className="text-body-sm text-fg-secondary">
              {t('shell.vehicle', { vehicleClass: data.vehicle_class, plate: data.vehicle_plate })}
            </p>
          )}
          {data.operator_identity_verified && (
            <p className="text-body-sm text-status-success-fg">{t('shell.operatorVerified')}</p>
          )}
        </Card>

        {isDelivered && <Alert tone="success">{t('shell.delivered')}</Alert>}

        {!isDelivered && (canConfirm || canReport) && (
          <div className="space-y-2">
            {canConfirm && (
              <Link to={`/r/${token}/confirm`}>
                <Button size="driver" fullWidth>
                  {t('shell.confirmReceipt')}
                </Button>
              </Link>
            )}
            {canReport && (
              <Link
                to={`/r/${token}/report-issue`}
                className="block text-center text-body-sm text-action-secondary-text underline"
              >
                {t('shell.reportProblem')}
              </Link>
            )}
          </div>
        )}

        <div className="flex items-center justify-between">
          <Button variant="secondary" size="compact" onClick={() => void view.refetch()} loading={view.isFetching}>
            {t('shell.checkStatus')}
          </Button>
        </div>
      </div>
    </div>
  );
}
