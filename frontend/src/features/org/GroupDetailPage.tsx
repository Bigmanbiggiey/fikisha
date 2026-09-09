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
      <Link to="/groups" className="text-sm text-brand-700">
        &larr; {t('org:common.back')}
      </Link>

      <Card>
        <div className="flex items-center justify-between gap-3">
          <h1 className="text-xl font-semibold text-slate-900">{group.data.name}</h1>
          <span className="flex gap-2">
            {group.data.my_role && <StatusBadge label={group.data.my_role} />}
            <StatusBadge
              tone={group.data.standing === 'GOOD' ? 'positive' : 'negative'}
              label={group.data.standing}
            />
          </span>
        </div>
        <p className="mt-1 text-sm text-slate-500">
          {group.data.type} · {group.data.assignment_mode}
        </p>
      </Card>

      <Card>
        <h2 className="text-sm font-medium text-slate-700">{t('org:groups.members')}</h2>
        <ul className="mt-2 divide-y divide-slate-100 text-sm">
          {(members.data?.data ?? []).map((m) => (
            <li key={m.id} className="flex items-center justify-between py-2">
              <span>{m.operator_name}</span>
              <span className="flex items-center gap-2">
                <StatusBadge label={m.role} />
                <StatusBadge
                  tone={m.status === 'ACTIVE' ? 'positive' : 'negative'}
                  label={m.status}
                />
                {canManage && m.status === 'ACTIVE' && m.role !== 'OWNER' && (
                  <Button
                    variant="ghost"
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
              className="rounded-lg border border-slate-300 px-2 py-2 text-sm"
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
            <Alert tone="error">{error}</Alert>
          </div>
        )}
      </Card>
    </div>
  );
}
