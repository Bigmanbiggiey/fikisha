import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';

import { useAuth } from '@/features/auth/useAuth';
import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { Field } from '@/components/Field';
import { Input } from '@/components/Input';
import { Modal } from '@/components/Modal';
import { PageLoader } from '@/components/PageLoader';
import { StatusBadge } from '@/components/StatusBadge';
import { CargoCategorySelect } from '@/features/jobs/CargoCategorySelect';
import { localizeError } from '@/services/errorMessage';

import { orgApi } from './orgApi';

export function BusinessesPage(): JSX.Element {
  const { user } = useAuth();
  const { t } = useTranslation(['org', 'errors']);
  const qc = useQueryClient();
  const [tradingName, setTradingName] = useState('');
  const [category, setCategory] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  // Registering submits the business for verification (D-1): say so.
  const [submittedId, setSubmittedId] = useState<string | null>(null);
  const navigate = useNavigate();

  const list = useQuery({ queryKey: ['businesses', user?.id], queryFn: orgApi.listBusinesses, retry: false });

  const create = useMutation({
    mutationFn: () =>
      orgApi.createBusiness(
        category ? { trading_name: tradingName.trim(), category } : { trading_name: tradingName.trim() },
      ),
    onSuccess: (created) => {
      setTradingName('');
      setCategory('');
      setFormError(null);
      setSubmittedId(created.id);
      void qc.invalidateQueries({ queryKey: ['businesses'] });
    },
    onError: (err) => setFormError(localizeError(err, t)),
  });

  function submit(e: FormEvent): void {
    e.preventDefault();
    if (tradingName.trim()) create.mutate();
  }

  return (
    <div className="space-y-5">
      <h1 className="text-h1 text-fg">{t('org:business.title')}</h1>

      <Card>
        <h2 className="text-label text-fg-secondary">{t('org:business.createTitle')}</h2>
        <form className="mt-3 flex flex-col gap-3 md:flex-row md:items-end" onSubmit={submit}>
          <div className="flex-1">
            <Field label={t('org:business.tradingName')}>
              {({ id }) => (
                <Input
                  id={id}
                  value={tradingName}
                  onChange={(e) => setTradingName(e.target.value)}
                  required
                />
              )}
            </Field>
          </div>
          {/* What the business mostly sends (D-4): the cargo categories. */}
          <div className="flex-1">
            <Field label={t('org:business.category')}>
              {(p) => <CargoCategorySelect {...p} value={category} onChange={setCategory} />}
            </Field>
          </div>
          <Button type="submit" loading={create.isPending} disabled={!tradingName.trim()}>
            {t('org:common.create')}
          </Button>
        </form>
        {formError && (
          <div className="mt-3">
            <Alert tone="danger">{formError}</Alert>
          </div>
        )}
      </Card>

      {list.isLoading ? (
        <PageLoader />
      ) : list.isError ? (
        <ErrorState message={localizeError(list.error, t)} error={list.error} onRetry={() => void list.refetch()} />
      ) : list.data && list.data.data.length > 0 ? (
        <ul className="space-y-2">
          {list.data.data.map((b) => (
            <li key={b.id}>
              <Link to={`/businesses/${b.id}`} className="block rounded-md">
                <Card interactive>
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-semibold text-fg">{b.trading_name}</span>
                    <span className="flex items-center gap-2">
                      {b.my_role && <StatusBadge tone="brand" label={b.my_role} />}
                      <StatusBadge
                        tone={b.standing === 'GOOD' ? 'success' : 'danger'}
                        icon={b.standing === 'GOOD' ? 'check' : 'alert'}
                        label={b.standing}
                      />
                    </span>
                  </div>
                </Card>
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState title={t('org:business.empty')} />
      )}

      <Modal
        open={submittedId !== null}
        onClose={() => setSubmittedId(null)}
        title={t('org:business.submittedTitle')}
        footer={
          <>
            <Button variant="secondary" onClick={() => setSubmittedId(null)}>
              {t('org:business.later')}
            </Button>
            <Button onClick={() => submittedId && navigate(`/businesses/${submittedId}`)}>
              {t('org:business.openBusiness')}
            </Button>
          </>
        }
      >
        <p className="text-body text-fg">{t('org:business.submittedBody')}</p>
      </Modal>
    </div>
  );
}
