import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ErrorState } from '@/components/ErrorState';
import { JobStatusChip } from '@/components/JobStatusChip';
import { PageLoader } from '@/components/PageLoader';
import type { JobState } from '@/design/tokens';
import { localizeError } from '@/services/errorMessage';
import { formatDateTime } from '@/services/datetime';

import { AccountStateBadge } from './AccountStateBadge';
import { AdminActionDialog } from './AdminActionDialog';
import { adminApi } from './adminApi';
import {
  KIND_TO_ACCOUNT,
  type AccountType,
  type DirectoryDetail,
  type DirectoryKind,
  type Intervention,
  type InterventionAction,
} from './types';

interface PendingAction {
  accountType: AccountType;
  accountId: string;
  action: InterventionAction;
}

/** Which actions an account in a given state offers (mirrors the server's
 * rules in `admin_console.services`; the server decides). Businesses and
 * groups can't be offboarded; an offboarded account offers nothing. */
function actionsFor(accountType: AccountType, state: string | undefined): InterventionAction[] {
  if (!state || state === 'OFFBOARDED') return [];
  const offboardable = accountType === 'USER' || accountType === 'OPERATOR';
  const actions: InterventionAction[] = [state === 'SUSPENDED' ? 'REINSTATE' : 'SUSPEND'];
  if (offboardable) actions.push('OFFBOARD');
  return actions;
}

/**
 * One business, operator or group (P3 §19.5): facts, members, its jobs that
 * are still running, the suspend / reinstate / offboard actions (§19.2
 * shell) for the account and for its person, and the history of every
 * such action. The phone is masked until an audited reveal.
 */
export function DirectoryDetailPage(): JSX.Element {
  const { t } = useTranslation(['admin', 'jobs', 'errors']);
  const { kind = 'businesses', id = '' } = useParams<{ kind: DirectoryKind; id: string }>();
  const qc = useQueryClient();
  const [pending, setPending] = useState<PendingAction | null>(null);

  const detail = useQuery({
    queryKey: ['admin', 'directory', kind, id],
    queryFn: () => adminApi.detail(kind, id),
    retry: false,
  });
  const reveal = useMutation({ mutationFn: () => adminApi.revealContact(kind, id) });
  const intervene = useMutation({
    mutationFn: (input: { reason: string; durationDays: number | null }) =>
      adminApi.intervene({
        account_type: pending!.accountType,
        account_id: pending!.accountId,
        action: pending!.action,
        reason: input.reason,
        duration_days: input.durationDays,
      }),
    onSuccess: () => {
      setPending(null);
      void qc.invalidateQueries({ queryKey: ['admin', 'directory'] });
    },
  });

  if (detail.isLoading) return <PageLoader />;
  if (detail.isError || !detail.data) {
    return <ErrorState message={localizeError(detail.error, t)} error={detail.error} onRetry={() => void detail.refetch()} />;
  }
  const d: DirectoryDetail = detail.data;
  const accountType = KIND_TO_ACCOUNT[kind];
  const userId = d.user_id ?? d.owner_user_id;
  const userState = d.user_status ?? d.owner_user_status;
  const history = [...d.interventions, ...d.user_interventions].sort((a, b) => b.created_at.localeCompare(a.created_at));

  function open(target: AccountType, targetId: string, action: InterventionAction): void {
    intervene.reset();
    setPending({ accountType: target, accountId: targetId, action });
  }

  const subject = pending?.accountType === 'USER' ? t('admin:detail.personOf', { name: d.name }) : d.name;

  return (
    <div className="space-y-5">
      <Link to={`/admin/directory?kind=${kind}`} className="text-body-sm text-action-secondary-text underline">
        {t('admin:detail.back')}
      </Link>

      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-h1 text-fg">{d.name}</h1>
        <AccountStateBadge state={d.state} />
      </div>
      <p className="text-body-sm text-fg-muted">{t(`admin:directory.kindOne.${kind}`)}</p>

      <Card className="space-y-2">
        <h2 className="text-h3 text-fg">{t('admin:detail.contact')}</h2>
        {reveal.data ? (
          <p className="text-body text-fg">
            {reveal.data.name} · <a href={`tel:${reveal.data.phone}`} className="fk-numeric underline">{reveal.data.phone}</a>
          </p>
        ) : (
          <div className="flex flex-wrap items-center gap-3">
            <span className="fk-numeric text-body text-fg">{d.phone ?? '—'}</span>
            <Button variant="secondary" loading={reveal.isPending} onClick={() => reveal.mutate()}>
              {t('admin:detail.reveal')}
            </Button>
          </div>
        )}
        <p className="text-body-sm text-fg-muted">{t('admin:detail.revealHint')}</p>
        {reveal.isError && <Alert tone="danger">{localizeError(reveal.error, t)}</Alert>}
      </Card>

      <Card className="space-y-3">
        <h2 className="text-h3 text-fg">{t('admin:detail.actions')}</h2>
        <div className="flex flex-wrap gap-2">
          {actionsFor(accountType, d.state).map((action) => (
            <Button
              key={`account-${action}`}
              variant={action === 'REINSTATE' ? 'secondary' : 'destructive'}
              onClick={() => open(accountType, d.id, action)}
            >
              {t(`admin:actions.${action}.account`)}
            </Button>
          ))}
          {userId &&
            actionsFor('USER', userState).map((action) => (
              <Button
                key={`user-${action}`}
                variant={action === 'REINSTATE' ? 'secondary' : 'destructive'}
                onClick={() => open('USER', userId, action)}
              >
                {t(`admin:actions.${action}.user`)}
              </Button>
            ))}
        </div>
        {userState && (
          <p className="text-body-sm text-fg-muted">
            {t('admin:detail.userState')} <AccountStateBadge state={userState} />
          </p>
        )}
        <p className="text-body-sm text-fg-muted">{t('admin:detail.suspensionEffect')}</p>
      </Card>

      <Card className="space-y-2">
        <h2 className="text-h3 text-fg">{t('admin:detail.inFlightTitle')}</h2>
        {d.in_flight_jobs.length === 0 ? (
          <p className="text-body-sm text-fg-muted">{t('admin:detail.noInFlight')}</p>
        ) : (
          <ul className="space-y-2">
            {d.in_flight_jobs.map((job) => (
              <li key={job.id} className="flex flex-wrap items-center gap-2">
                <Link to={`/jobs/${job.id}`} className="fk-numeric text-body font-semibold text-action-secondary-text underline">
                  {job.reference}
                </Link>
                <JobStatusChip state={job.status as JobState} label={t(`jobs:status.${job.status}`)} />
              </li>
            ))}
          </ul>
        )}
      </Card>

      {d.members && d.members.length > 0 && (
        <Card className="space-y-2">
          <h2 className="text-h3 text-fg">{t('admin:detail.members')}</h2>
          <ul className="space-y-1">
            {d.members.map((m) => (
              <li key={m.user_id ?? m.operator_id} className="text-body-sm text-fg">
                {m.name || '—'} · {m.role} · {t(`admin:memberStatus.${m.status}`, { defaultValue: m.status })}
              </li>
            ))}
          </ul>
        </Card>
      )}

      <Card className="space-y-2">
        <h2 className="text-h3 text-fg">{t('admin:detail.history')}</h2>
        {history.length === 0 ? (
          <p className="text-body-sm text-fg-muted">{t('admin:detail.noHistory')}</p>
        ) : (
          <ul className="space-y-3">
            {history.map((h: Intervention) => (
              <li key={h.id} className="text-body-sm">
                <span className="font-semibold text-fg">
                  {t(`admin:actions.${h.action}.done`)} · {t(`admin:state.${h.before_state}`)} →{' '}
                  {t(`admin:state.${h.after_state}`)}
                </span>
                <span className="block text-fg-secondary">{h.reason}</span>
                <span className="block text-fg-muted">
                  {[h.admin_name, formatDateTime(h.created_at), h.duration_days ? t('admin:action.durationLabel', { count: h.duration_days }) : null]
                    .filter(Boolean)
                    .join(' · ')}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <AdminActionDialog
        open={pending !== null}
        onClose={() => setPending(null)}
        title={pending ? t(`admin:actions.${pending.action}.title`) : ''}
        restatement={pending ? t(`admin:actions.${pending.action}.restate`, { name: subject }) : ''}
        confirmLabel={pending ? t(`admin:actions.${pending.action}.confirm`) : ''}
        destructive={pending?.action !== 'REINSTATE'}
        allowDuration={pending?.action === 'SUSPEND'}
        pending={intervene.isPending}
        error={intervene.error}
        onConfirm={(input) => intervene.mutate(input)}
      />
    </div>
  );
}
