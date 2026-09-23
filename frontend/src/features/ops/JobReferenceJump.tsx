import { useMutation } from '@tanstack/react-query';
import { type FormEvent, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Input } from '@/components/Input';
import { localizeError } from '@/services/errorMessage';

import { opsApi } from './opsApi';

/**
 * §18.4 Search, founder-scoped to a job-reference "quick jump" this
 * increment (full cross-entity search is its own later increment). Accepts
 * the 6-char reference the business/operator UI shows or the recipient
 * page's 8-char one — the backend matches by id suffix. One match opens the
 * job; several open the monitor filtered to that reference.
 */
export function JobReferenceJump(): JSX.Element {
  const { t } = useTranslation(['ops', 'errors']);
  const navigate = useNavigate();
  const [ref, setRef] = useState('');
  const [message, setMessage] = useState<string | null>(null);

  const jump = useMutation({
    mutationFn: (value: string) => opsApi.monitor({ ref: value }),
    onSuccess: (page, value) => {
      if (page.data.length === 1) navigate(`/jobs/${page.data[0]!.id}`);
      else if (page.data.length > 1) navigate(`/ops/jobs?ref=${encodeURIComponent(value)}`);
      else setMessage(t('ops:jump.notFound', { ref: value }));
    },
  });

  function onSubmit(e: FormEvent): void {
    e.preventDefault();
    const value = ref.trim();
    setMessage(null);
    if (value.replace(/[^0-9a-fA-F]/g, '').length < 4) {
      setMessage(t('ops:jump.tooShort'));
      return;
    }
    jump.mutate(value);
  }

  return (
    <form onSubmit={onSubmit} role="search" className="space-y-2">
      <label htmlFor="job-ref-jump" className="block text-label text-fg-secondary">
        {t('ops:jump.label')}
      </label>
      <div className="flex gap-2">
        <Input
          id="job-ref-jump"
          value={ref}
          onChange={(e) => setRef(e.target.value)}
          placeholder={t('ops:jump.placeholder')}
          autoComplete="off"
          className="max-w-xs uppercase"
        />
        <Button type="submit" variant="secondary" loading={jump.isPending}>
          {t('ops:jump.go')}
        </Button>
      </div>
      {message && (
        <p role="status" className="text-body-sm text-fg-secondary">
          {message}
        </p>
      )}
      {jump.isError && <Alert tone="danger">{localizeError(jump.error, t)}</Alert>}
    </form>
  );
}
