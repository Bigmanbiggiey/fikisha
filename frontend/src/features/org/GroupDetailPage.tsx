import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ErrorState } from '@/components/ErrorState';
import { Field } from '@/components/Field';
import { Input } from '@/components/Input';
import { PageLoader } from '@/components/PageLoader';
import { StatusBadge } from '@/components/StatusBadge';
import { localizeError } from '@/services/errorMessage';

import { orgApi } from './orgApi';
import { GROUP_ROLES } from './types';

export function GroupDetailPage(): JSX.Element {
  const { groupId = '' } = useParams();
  const { t } = useTranslation(['org', 'errors']);
  const qc = useQueryClient();

  const group = useQuery({
    queryKey: ['group', groupId],
    queryFn: () => orgApi.getGroup(groupId),
    retry: false,
  });
  const members = useQuery({
    queryKey: ['group', groupId, 'members'],
    queryFn: () => orgApi.listGroupMembers(groupId),
    enabled: group.isSuccess,
    retry: false,
  });

  const canManage = group.data?.my_role === 'OWNER' || group.data?.my_role === 'MANAGER';

  const [operatorId, setOperatorId] = useState('');
  const [role, setRole] = useState<string>('DRIVER');
  const [error, setError] = useState<string | null>(null);
  const addMember = useMutation({
    mutationFn: () => orgApi.addGroupMember(groupId, { operator_id: operatorId.trim(), role }),
    onSuccess: () => {
      setOperatorId('');
      setError(null);
      void qc.invalidateQueries({ queryKey: ['group', groupId, 'members'] });
    },
    onError: (err) => setError(localizeError(err, t)),
  });

  if (group.isLoading) return <PageLoader />;
  if (group.isError || !group.data) {
    return (
      <ErrorState message={localizeError(group.error, t)} onRetry={() => void group.refetch()} />
    );
  }

  return (
    <div className="space-y-5">
      <Link to="/groups" className="text-body-sm text-action-secondary-text">
        &larr; {t('org:common.back')}
      </Link>

      <Card>
        <div className="flex items-center justify-between gap-3">
          <h1 className="text-h1 text-fg">{group.data.name}</h1>
          <span className="flex flex-wrap gap-2">
            {group.data.my_role && <StatusBadge tone="brand" label={group.data.my_role} />}
            <StatusBadge
              tone={group.data.standing === 'GOOD' ? 'success' : 'danger'}
              icon={group.data.standing === 'GOOD' ? 'check' : 'alert'}
              label={group.data.standing}
            />
          </span>
        </div>
        <p className="mt-1 text-body-sm text-fg-muted">
          {group.data.type} · {group.data.assignment_mode}
        </p>
      </Card>

      <Card>
        <h2 className="text-label text-fg-secondary">{t('org:groups.members')}</h2>
        <ul className="mt-2 divide-y divide-line text-body-sm">
          {(members.data?.data ?? []).map((m) => (
            <li key={m.id} className="flex items-center justify-between py-2">
              <span>{m.operator_name}</span>
              <span className="flex items-center gap-2">
                <StatusBadge tone="brand" label={m.role} />
                <StatusBadge
                  tone={m.status === 'ACTIVE' ? 'success' : 'neutral'}
                  icon={m.status === 'ACTIVE' ? 'check' : undefined}
                  label={m.status}
                />
                {canManage && m.status === 'ACTIVE' && m.role !== 'OWNER' && (
                  <Button
                    variant="destructive"
                    size="compact"
                    onClick={() =>
                      orgApi
                        .removeGroupMember(groupId, m.id)
                        .then(() =>
                          qc.invalidateQueries({ queryKey: ['group', groupId, 'members'] }),
                        )
                        .catch(() => undefined)
                    }
                  >
                    {t('org:common.remove')}
                  </Button>
                )}
              </span>
            </li>
          ))}
        </ul>

        {canManage && (
          <form
            className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-end"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              if (operatorId.trim()) addMember.mutate();
            }}
          >
            <div className="flex-1">
              <Field label={t('org:groups.memberOperatorId')}>
                {({ id }) => (
                  <Input
                    id={id}
                    value={operatorId}
                    onChange={(e) => setOperatorId(e.target.value)}
                  />
                )}
              </Field>
            </div>
            <select
              className="min-h-target rounded-md border border-line-strong bg-surface-input px-2 text-body-sm text-fg"
              value={role}
              onChange={(e) => setRole(e.target.value)}
            >
              {GROUP_ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
            <Button type="submit" loading={addMember.isPending}>
              {t('org:common.add')}
            </Button>
          </form>
        )}
        {error && (
          <div className="mt-2">
            <Alert tone="danger">{error}</Alert>
          </div>
        )}
      </Card>
    </div>
  );
}
