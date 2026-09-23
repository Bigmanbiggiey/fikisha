import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { Modal } from '@/components/Modal';
import { PageLoader } from '@/components/PageLoader';
import { StatusBadge } from '@/components/StatusBadge';
import { useAuth } from '@/features/auth/useAuth';
import { isPlatformAdmin } from '@/features/auth/staff';
import { formatKes } from '@/features/jobs/money';
import { localizeError } from '@/services/errorMessage';

import { opsApi } from './opsApi';
import { textareaClass } from './StaffJobPanel';
import type { HighValueDecision, HighValueRow } from './types';

/**
 * §18.3 High-value review. The gate is server-side (`decide_high_value` +
 * the `HighValueApproved` assignment guard); this screen mirrors it: an Ops
 * Officer decides HIGH, a Platform Admin decides VERY_HIGH, so the decide
 * control is *hidden* (not disabled) on a VERY_HIGH row for an Ops Officer.
 * Every decision carries a reason. A rejection is permanent (there is no
 * correction path in the backend), and the confirm step says so plainly.
 * No new eligibility rules: driver/vehicle eligibility still runs at
 * assignment.
 */
export function HighValueReviewPage(): JSX.Element {
  const { t } = useTranslation(['ops', 'errors']);
  const { user } = useAuth();
  const platformAdmin = isPlatformAdmin(user);
  const qc = useQueryClient();
  const [active, setActive] = useState<HighValueRow | null>(null);
  const [decision, setDecision] = useState<HighValueDecision>('APPROVED');
  const [rationale, setRationale] = useState('');
  const [done, setDone] = useState(false);

  const queue = useQuery({ queryKey: ['ops', 'high-value'], queryFn: () => opsApi.highValueQueue(), retry: false });

  const decide = useMutation({
    mutationFn: () => opsApi.decideHighValue(active!.id, decision, rationale.trim()),
    onSuccess: () => {
      setActive(null);
      setDone(true);
      void qc.invalidateQueries({ queryKey: ['ops'] });
    },
  });

  function open(row: HighValueRow): void {
    setActive(row);
    setDecision('APPROVED');
    setRationale('');
    setDone(false);
    decide.reset();
  }

  if (queue.isLoading) return <PageLoader />;
  if (queue.isError) {
    return <ErrorState message={localizeError(queue.error, t)} onRetry={() => void queue.refetch()} />;
  }
  const rows = queue.data?.data ?? [];

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-h1 text-fg">{t('ops:highValue.title')}</h1>
        <p className="mt-1 text-body-sm text-fg-secondary">{t('ops:highValue.intro')}</p>
      </div>
      {done && (
        <p role="status" className="text-body-sm text-fg-secondary">
          {t('ops:highValue.decided')}
        </p>
      )}

      {rows.length === 0 ? (
        <EmptyState title={t('ops:highValue.empty')} />
      ) : (
        <ul className="space-y-3">
          {rows.map((row) => (
            <li key={row.id}>
              <Card className="space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <Link to={`/jobs/${row.id}`} className="fk-numeric text-h3 text-action-secondary-text underline">
                    {row.reference}
                  </Link>
                  <StatusBadge
                    tone={row.needs_platform_admin ? 'warning' : 'info'}
                    icon={row.needs_platform_admin ? 'lock' : 'flag'}
                    label={t(`ops:band.${row.value_band ?? 'none'}`)}
                  />
                </div>
                <dl className="grid grid-cols-1 gap-1 text-body-sm sm:grid-cols-2">
                  <div>
                    <dt className="inline text-fg-muted">{t('ops:highValue.declared')}: </dt>
                    <dd className="inline fk-numeric text-fg">{formatKes(row.declared_value_kes)}</dd>
                  </div>
                  <div>
                    <dt className="inline text-fg-muted">{t('ops:highValue.operator')}: </dt>
                    <dd className="inline text-fg">{row.operator_name ?? '—'}</dd>
                  </div>
                  <div className="sm:col-span-2 text-fg-secondary">{row.business_name}</div>
                </dl>
                {row.needs_platform_admin && !platformAdmin ? (
                  <p className="text-body-sm text-fg-secondary">{t('ops:highValue.platformAdminDecides')}</p>
                ) : (
                  <Button size="compact" variant="secondary" onClick={() => open(row)}>
                    {t('ops:highValue.decide')}
                  </Button>
                )}
              </Card>
            </li>
          ))}
        </ul>
      )}

      <Modal
        open={!!active}
        onClose={() => setActive(null)}
        title={active ? t('ops:highValue.modalTitle', { ref: active.reference }) : ''}
        footer={
          <>
            <Button variant="secondary" onClick={() => setActive(null)}>
              {t('ops:staff.keep')}
            </Button>
            <Button
              variant={decision === 'REJECTED' ? 'destructive' : 'primary'}
              disabled={!rationale.trim()}
              loading={decide.isPending}
              onClick={() => decide.mutate()}
            >
              {decision === 'REJECTED' ? t('ops:highValue.confirmReject') : t('ops:highValue.confirmApprove')}
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <p className="text-body-sm text-fg-secondary">{t('ops:highValue.eligibilityNote')}</p>
          <fieldset className="flex gap-4">
            <legend className="sr-only">{t('ops:highValue.decide')}</legend>
            {(['APPROVED', 'REJECTED'] as const).map((value) => (
              <label key={value} className="flex min-h-target items-center gap-2 text-body text-fg">
                <input
                  type="radio"
                  name="hv-decision"
                  value={value}
                  checked={decision === value}
                  onChange={() => setDecision(value)}
                />
                {value === 'APPROVED' ? t('ops:highValue.approve') : t('ops:highValue.reject')}
              </label>
            ))}
          </fieldset>
          {decision === 'REJECTED' && <Alert tone="warning">{t('ops:highValue.rejectWarning')}</Alert>}
          <label htmlFor="hv-rationale" className="block text-label text-fg-secondary">
            {t('ops:highValue.rationale')}
          </label>
          <textarea
            id="hv-rationale"
            value={rationale}
            maxLength={2000}
            onChange={(e) => setRationale(e.target.value)}
            className={textareaClass}
          />
          {decide.isError && <Alert tone="danger">{localizeError(decide.error, t)}</Alert>}
        </div>
      </Modal>
    </div>
  );
}
