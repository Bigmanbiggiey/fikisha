import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { Field } from '@/components/Field';
import { Input } from '@/components/Input';
import { PageLoader } from '@/components/PageLoader';
import { StatusBadge } from '@/components/StatusBadge';
import { ApiError } from '@/services/problem';
import { localizeError } from '@/services/errorMessage';

import { orgApi } from './orgApi';

export function OperatorProfilePage(): JSX.Element {
  const { t } = useTranslation(['org', 'errors']);
  const qc = useQueryClient();

  const profile = useQuery({
    queryKey: ['operator', 'me'],
    queryFn: orgApi.getMyOperator,
    retry: (count, err) => !(err instanceof ApiError && err.status === 404) && count < 1,
  });

  const missing = profile.isError && profile.error instanceof ApiError && profile.error.status === 404;

  const [fullName, setFullName] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () =>
      orgApi.createOperator({ full_name: fullName.trim(), display_name: displayName.trim() }),
    onSuccess: () => {
      setError(null);
      void qc.invalidateQueries({ queryKey: ['operator', 'me'] });
    },
    onError: (err) => setError(localizeError(err, t)),
  });

  if (profile.isLoading) return <PageLoader />;

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold text-slate-900">{t('org:operator.title')}</h1>

      {profile.isSuccess ? (
        <Card>
          <div className="flex items-center justify-between">
            <span className="font-medium text-slate-900">{profile.data.full_name}</span>
            <StatusBadge
              tone={profile.data.status === 'ACTIVE' ? 'positive' : 'neutral'}
              label={profile.data.status}
            />
          </div>
          <p className="mt-1 text-sm text-slate-500">{profile.data.user_phone}</p>
          <Alert tone="success">{t('org:operator.haveProfile')}</Alert>
        </Card>
      ) : missing ? (
        <Card>
          <h2 className="text-sm font-medium text-slate-700">{t('org:operator.createTitle')}</h2>
          <p className="mt-1 text-sm text-slate-500">{t('org:operator.noProfile')}</p>
          <form
            className="mt-3 space-y-3"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              if (fullName.trim()) create.mutate();
            }}
          >
            <Field label={t('org:operator.fullName')}>
              {({ id }) => (
                <Input id={id} value={fullName} onChange={(e) => setFullName(e.target.value)} required />
              )}
            </Field>
            <Field label={t('org:operator.displayName')}>
              {({ id }) => (
                <Input
                  id={id}
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                />
              )}
            </Field>
            <Button type="submit" loading={create.isPending} disabled={!fullName.trim()}>
              {t('org:common.create')}
            </Button>
            {error && <Alert tone="error">{error}</Alert>}
          </form>
        </Card>
      ) : (
        <Alert tone="error">{localizeError(profile.error, t)}</Alert>
      )}
    </div>
  );
}
