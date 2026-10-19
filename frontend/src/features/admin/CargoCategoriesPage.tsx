import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { Field } from '@/components/Field';
import { Input } from '@/components/Input';
import { PageLoader } from '@/components/PageLoader';
import { Select } from '@/components/Select';
import { useCargoCategoryLabel } from '@/features/jobs/cargoCategoryLabel';
import { jobsApi } from '@/features/jobs/jobsApi';
import { formatDateTime } from '@/services/datetime';
import { localizeError } from '@/services/errorMessage';

import { adminApi, type UncategorisedCargo } from './adminApi';

/**
 * Teaching the cargo-category matcher (assessment 2026-10-19 D-5): what it
 * filed under Other, and a keyword or a new category from a Platform Admin.
 * Each is a versioned, audited config change behind a fresh MFA code; the
 * system never adds a category on its own.
 */
export function CargoCategoriesPage(): JSX.Element {
  const { t } = useTranslation(['admin', 'errors']);
  const list = useQuery({ queryKey: ['admin', 'cargo-uncategorised'], queryFn: adminApi.uncategorisedCargo });
  const categories = useQuery({ queryKey: ['reference', 'cargoCategories'], queryFn: jobsApi.cargoCategories });
  const codes = (categories.data?.data ?? []).map((c) => c.code).filter((c) => c !== 'OTHER');

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-h1 text-fg">{t('admin:cargo.title')}</h1>
        <p className="mt-1 text-body-sm text-fg-secondary">{t('admin:cargo.intro')}</p>
      </div>
      {list.isLoading || categories.isLoading ? (
        <PageLoader />
      ) : list.isError ? (
        <ErrorState message={localizeError(list.error, t)} error={list.error} onRetry={() => void list.refetch()} />
      ) : (list.data?.data ?? []).length === 0 ? (
        <EmptyState title={t('admin:cargo.empty')} />
      ) : (
        <ul className="space-y-3">
          {list.data!.data.map((row) => (
            <li key={row.description}>
              <TeachRow row={row} codes={codes} />
            </li>
          ))}
        </ul>
      )}
      <NewCategory />
    </div>
  );
}

function firstWord(description: string): string {
  return (
    description
      .toLowerCase()
      .split(/[^\p{L}']+/u)
      .find((w) => w.length >= 3) ?? ''
  );
}

function TeachRow({ row, codes }: { row: UncategorisedCargo; codes: string[] }): JSX.Element {
  const { t } = useTranslation(['admin', 'errors']);
  const label = useCargoCategoryLabel();
  const qc = useQueryClient();
  const [category, setCategory] = useState(codes[0] ?? '');
  const [keyword, setKeyword] = useState(firstWord(row.description));
  const [reason, setReason] = useState(t('admin:cargo.defaultReason'));
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const teach = useMutation({
    mutationFn: () => adminApi.addCargoKeyword({ category_code: category, keyword, rationale: reason }),
    onSuccess: () => {
      setError(null);
      setDone(t('admin:cargo.added', { keyword: keyword.trim().toLowerCase(), category: label(category) }));
      void qc.invalidateQueries({ queryKey: ['admin', 'cargo-uncategorised'] });
      void qc.invalidateQueries({ queryKey: ['reference'] });
    },
    onError: (e) => setError(localizeError(e, t)),
  });

  function submit(e: FormEvent): void {
    e.preventDefault();
    if (category && keyword.trim()) teach.mutate();
  }

  return (
    <Card>
      <p className="font-semibold text-fg">{row.description}</p>
      <p className="text-body-sm text-fg-muted">
        {t('admin:cargo.times', { count: row.count })} · {t('admin:cargo.lastSeen', { when: formatDateTime(row.last_seen) })}
      </p>
      <form className="mt-3 grid gap-3 md:grid-cols-3" onSubmit={submit}>
        <Field label={t('admin:cargo.category')}>
          {(p) => (
            <Select {...p} value={category} onChange={(e) => setCategory(e.target.value)}>
              {codes.map((c) => (
                <option key={c} value={c}>
                  {label(c)}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field label={t('admin:cargo.keyword')}>
          {(p) => <Input {...p} value={keyword} onChange={(e) => setKeyword(e.target.value)} />}
        </Field>
        <Field label={t('admin:cargo.reason')}>
          {(p) => <Input {...p} value={reason} onChange={(e) => setReason(e.target.value)} />}
        </Field>
        <div className="md:col-span-3">
          <Button type="submit" loading={teach.isPending} disabled={!category || !keyword.trim()}>
            {t('admin:cargo.addKeyword')}
          </Button>
        </div>
      </form>
      {done && <Alert tone="success">{done}</Alert>}
      {error && <Alert tone="danger">{error}</Alert>}
    </Card>
  );
}

function NewCategory(): JSX.Element {
  const { t } = useTranslation(['admin', 'errors']);
  const qc = useQueryClient();
  const [code, setCode] = useState('');
  const [keywords, setKeywords] = useState('');
  const [reason, setReason] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const add = useMutation({
    mutationFn: () =>
      adminApi.addCargoCategory({
        code: code.trim().toUpperCase(),
        keywords: keywords
          .split(',')
          .map((k) => k.trim())
          .filter(Boolean),
        rationale: reason,
      }),
    onSuccess: (r) => {
      setError(null);
      setDone(t('admin:cargo.categoryAdded', { code: r.code }));
      setCode('');
      setKeywords('');
      void qc.invalidateQueries({ queryKey: ['reference'] });
      void qc.invalidateQueries({ queryKey: ['admin', 'cargo-uncategorised'] });
    },
    onError: (e) => setError(localizeError(e, t)),
  });

  return (
    <Card>
      <h2 className="text-h3 text-fg">{t('admin:cargo.newTitle')}</h2>
      <form
        className="mt-3 grid gap-3 md:grid-cols-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (code.trim()) add.mutate();
        }}
      >
        <Field label={t('admin:cargo.newCode')}>
          {(p) => <Input {...p} value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} />}
        </Field>
        <Field label={t('admin:cargo.newKeywords')}>
          {(p) => <Input {...p} value={keywords} onChange={(e) => setKeywords(e.target.value)} />}
        </Field>
        <Field label={t('admin:cargo.reason')}>
          {(p) => <Input {...p} value={reason} onChange={(e) => setReason(e.target.value)} />}
        </Field>
        <div className="md:col-span-3">
          <Button type="submit" variant="secondary" loading={add.isPending} disabled={!code.trim()}>
            {t('admin:cargo.addCategory')}
          </Button>
        </div>
      </form>
      {done && <Alert tone="success">{done}</Alert>}
      {error && <Alert tone="danger">{error}</Alert>}
    </Card>
  );
}
