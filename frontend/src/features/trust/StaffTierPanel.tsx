import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { Select } from '@/components/Select';
import { AdminActionDialog } from '@/features/admin/AdminActionDialog';
import { isPlatformAdmin } from '@/features/auth/staff';
import { useAuth } from '@/features/auth/useAuth';
import { localizeError } from '@/services/errorMessage';

import { TierCard } from './TierCard';
import { trustApi } from './trustApi';
import { STORED_TIERS, type StoredTier, type TierView } from './types';

type Pending = { kind: 'set'; level: StoredTier } | { kind: 'decide'; confirm: boolean; changeId: string };

/**
 * An operator's tier for Fikisha staff (operator-tiers plan T-4): the card,
 * plus, for a Platform Admin, the open proposal (confirm / reject) and a
 * direct promote / demote (TD-1, recorded as manual). Each needs a reason
 * and a fresh authenticator code; the server enforces both. An Operations
 * Officer sees the same card, read only.
 */
export function StaffTierPanel({ operatorId }: { operatorId: string }): JSX.Element | null {
  const { t } = useTranslation(['trust', 'admin', 'errors']);
  const { user } = useAuth();
  const admin = isPlatformAdmin(user);
  const qc = useQueryClient();
  const key = ['operator-tier', operatorId];
  const tier = useQuery({ queryKey: key, queryFn: () => trustApi.tier(operatorId), retry: false });
  const [target, setTarget] = useState<StoredTier | ''>('');
  const [pending, setPending] = useState<Pending | null>(null);

  const act = useMutation({
    mutationFn: (reason: string): Promise<TierView> => {
      if (pending?.kind === 'set') return trustApi.setTier(operatorId, { level: pending.level, reason });
      if (pending?.kind === 'decide') {
        return trustApi.decide(pending.changeId, { decision: pending.confirm ? 'CONFIRM' : 'REJECT', reason });
      }
      return Promise.reject(new Error('no action'));
    },
    onSuccess: (view) => {
      qc.setQueryData(key, view);
      void qc.invalidateQueries({ queryKey: ['tier-proposals'] });
      setPending(null);
      setTarget('');
    },
  });

  if (tier.isLoading) return null;
  if (tier.isError || !tier.data) {
    return (
      <Card>
        <Alert tone="danger">{localizeError(tier.error, t)}</Alert>
      </Card>
    );
  }
  const view = tier.data;
  const name = view.operator_name;
  const lvl = (l: string): string => t(`trust:level.${l}`);
  const proposal = view.open_proposal;

  function open(p: Pending): void {
    act.reset();
    setPending(p);
  }

  let title = '';
  let restatement = '';
  let confirmLabel = '';
  let destructive = false;
  if (pending?.kind === 'set') {
    const down = rank(pending.level) < rank(view.stored_level);
    title = t(down ? 'trust:admin.demoteTitle' : 'trust:admin.promoteTitle');
    restatement = t('trust:admin.setRestate', { name, from: lvl(view.stored_level), to: lvl(pending.level) });
    confirmLabel = t(down ? 'trust:admin.demote' : 'trust:admin.promote');
    destructive = down;
  } else if (pending?.kind === 'decide' && proposal) {
    title = t(pending.confirm ? 'trust:admin.confirmTitle' : 'trust:admin.rejectTitle');
    restatement = t(pending.confirm ? 'trust:admin.confirmRestate' : 'trust:admin.rejectRestate', {
      name,
      to: lvl(proposal.to_level),
    });
    confirmLabel = t(pending.confirm ? 'trust:admin.confirm' : 'trust:admin.reject');
    destructive = !pending.confirm;
  }

  return (
    <div className="space-y-3">
      <TierCard view={view} staff />
      {admin && (
        <Card className="space-y-3">
          <h2 className="text-h3 text-fg">{t('trust:admin.title')}</h2>
          {proposal && (
            <div className="space-y-2 rounded-md bg-surface-sunken p-3">
              <p className="text-body text-fg">
                {t('trust:admin.proposal', { from: lvl(proposal.from_level), to: lvl(proposal.to_level) })}
              </p>
              <div className="flex flex-wrap gap-2">
                <Button onClick={() => open({ kind: 'decide', confirm: true, changeId: proposal.id })}>
                  {t('trust:admin.confirm')}
                </Button>
                <Button variant="secondary" onClick={() => open({ kind: 'decide', confirm: false, changeId: proposal.id })}>
                  {t('trust:admin.reject')}
                </Button>
              </div>
            </div>
          )}
          <div className="flex flex-wrap items-end gap-2">
            <div className="space-y-1">
              <label htmlFor="tier-target" className="block text-label text-fg-secondary">
                {t('trust:admin.changeTo')}
              </label>
              <Select id="tier-target" inline value={target} onChange={(e) => setTarget(e.target.value as StoredTier | '')}>
                <option value="">{t('trust:admin.choose')}</option>
                {STORED_TIERS.filter((l) =>
                  // TD-4: leaving Restricted goes back to L1 only
                  view.stored_level === 'RESTRICTED' ? l === 'L1' : l !== view.stored_level,
                ).map((l) => (
                  <option key={l} value={l}>
                    {lvl(l)}
                  </option>
                ))}
              </Select>
            </div>
            <Button variant="secondary" disabled={!target} onClick={() => target && open({ kind: 'set', level: target })}>
              {t('trust:admin.change')}
            </Button>
          </div>
          <p className="text-body-sm text-fg-muted">{t('trust:admin.hint')}</p>
        </Card>
      )}
      <AdminActionDialog
        open={pending !== null}
        onClose={() => setPending(null)}
        title={title}
        restatement={restatement}
        confirmLabel={confirmLabel}
        destructive={destructive}
        pending={act.isPending}
        error={act.error}
        onConfirm={({ reason }) => act.mutate(reason)}
      />
    </div>
  );
}

function rank(level: string): number {
  return { RESTRICTED: 0, L1: 1, L2: 2, L3: 3 }[level] ?? 0;
}
