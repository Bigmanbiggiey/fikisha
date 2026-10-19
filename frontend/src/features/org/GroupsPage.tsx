import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { useAuth } from '@/features/auth/useAuth';
import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { Field } from '@/components/Field';
import { Input } from '@/components/Input';
import { PageLoader } from '@/components/PageLoader';
import { StatusBadge } from '@/components/StatusBadge';
import { Select } from '@/components/Select';
import { localizeError } from '@/services/errorMessage';

import { orgApi } from './orgApi';
import { GROUP_TYPES } from './types';

export function GroupsPage(): JSX.Element {
  const { user } = useAuth();
  const { t } = useTranslation(['org', 'errors']);
  const qc = useQueryClient();

  const list = useQuery({ queryKey: ['groups', user?.id], queryFn: orgApi.listGroups, retry: false });

  const [name, setName] = useState('');
  const [type, setType] = useState<string>('SACCO');
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () => orgApi.createGroup({ name: name.trim(), type }),
    onSuccess: () => {
      setName('');
      setError(null);
      void qc.invalidateQueries({ queryKey: ['groups'] });
    },
    onError: (err) => setError(localizeError(err, t)),
  });

  return (
    <div className="space-y-5">
      <h1 className="text-h1 text-fg">{t('org:groups.title')}</h1>

      <Card>
        <h2 className="text-label text-fg-secondary">{t('org:groups.createTitle')}</h2>
        <p className="mt-1 text-caption text-fg-muted">{t('org:groups.needProfile')}</p>
        <form
          className="mt-3 flex flex-col gap-2 md:flex-row md:items-end"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            if (name.trim()) create.mutate();
          }}
        >
          <div className="flex-1">
            <Field label={t('org:groups.groupName')}>
              {({ id }) => (
                <Input id={id} value={name} onChange={(e) => setName(e.target.value)} required />
              )}
            </Field>
          </div>
          <Select
            inline
            aria-label={t('org:groups.groupType')}
            value={type}
            onChange={(e) => setType(e.target.value)}
          >
            {GROUP_TYPES.map((ty) => (
              <option key={ty} value={ty}>
                {ty}
              </option>
            ))}
          </Select>
          <Button type="submit" loading={create.isPending} disabled={!name.trim()}>
            {t('org:common.create')}
          </Button>
        </form>
        {error && (
          <div className="mt-2">
            <Alert tone="danger">{error}</Alert>
          </div>
        )}
      </Card>

      {list.isLoading ? (
        <PageLoader />
      ) : list.isError ? (
        <ErrorState message={localizeError(list.error, t)} error={list.error} onRetry={() => void list.refetch()} />
      ) : list.data && list.data.data.length > 0 ? (
        <ul className="space-y-2">
          {list.data.data.map((g) => (
            <li key={g.id}>
              <Link to={`/groups/${g.id}`} className="block rounded-md">
                <Card interactive>
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-semibold text-fg">{g.name}</span>
                    <span className="flex gap-2">
                      {g.my_role && <StatusBadge label={g.my_role} />}
                      <StatusBadge label={g.type} />
                    </span>
                  </div>
                </Card>
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState title={t('org:groups.empty')} />
      )}
    </div>
  );
}
