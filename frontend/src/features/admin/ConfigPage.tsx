import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ErrorState } from '@/components/ErrorState';
import { Input } from '@/components/Input';
import { PageLoader } from '@/components/PageLoader';
import { formatKes } from '@/features/jobs/money';
import { localizeError } from '@/services/errorMessage';
import { formatDateTime } from '@/services/datetime';

import { AdminActionDialog } from './AdminActionDialog';
import { adminApi } from './adminApi';
import type { ConfigPreview } from './types';

/** How each editable value is shown and typed. The API speaks raw config
 * units (a 0–1 rate, KES minor units, whole hours/days/minutes); people
 * type a percentage and whole shillings. */
type Unit = 'percent' | 'kes' | 'hours' | 'days' | 'minutes';
const UNIT: Record<string, Unit> = {
  'commission.rate': 'percent',
  'commission.min_fee_kes': 'kes',
  'commission.cap_kes': 'kes',
  'timeouts.post_completion_window.high_and_latent_days': 'days',
  'timeouts.stale_assignment_alert_minutes': 'minutes',
};
const unitOf = (path: string): Unit => UNIT[path] ?? 'hours';

function read(config: Record<string, unknown>, path: string): unknown {
  return path.split('.').reduce<unknown>((node, key) => (node as Record<string, unknown> | undefined)?.[key], config);
}

function toInput(path: string, value: unknown): string {
  if (typeof value !== 'number') return '';
  switch (unitOf(path)) {
    case 'percent':
      return String(Math.round(value * 10000) / 100);
    case 'kes':
      return String(value / 100);
    default:
      return String(value);
  }
}

/** Typed text → config units, or null when it isn't a valid number. */
function fromInput(path: string, text: string): number | null {
  const trimmed = text.trim();
  if (!/^\d+(\.\d+)?$/.test(trimmed)) return null;
  const n = Number(trimmed);
  switch (unitOf(path)) {
    case 'percent':
      return n <= 100 ? Math.round(n * 100) / 10000 : null;
    case 'kes':
      return Math.round(n * 100);
    default:
      return Number.isInteger(n) ? n : null;
  }
}

function display(path: string, value: unknown, t: (key: string, o?: Record<string, unknown>) => string): string {
  if (typeof value !== 'number') return String(value ?? '—');
  switch (unitOf(path)) {
    case 'percent':
      return `${Math.round(value * 10000) / 100}%`;
    case 'kes':
      return formatKes(value);
    default:
      return t(`admin:config.unit.${unitOf(path)}`, { count: value });
  }
}

/**
 * Configuration (P3 §19.3, Increment 9 D-3). The live config, read-only,
 * plus a single-admin draft → diff → apply flow for the allowlisted keys
 * (commission and timeouts). Applying needs a reason and a fresh MFA
 * step-up, which the server refuses until admin MFA exists. Value bands,
 * permissions, vehicle classes and verification rules stay read-only.
 */
export function ConfigPage(): JSX.Element {
  const { t } = useTranslation(['admin', 'errors']);
  const qc = useQueryClient();
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [preview, setPreview] = useState<ConfigPreview | null>(null);
  const [applyOpen, setApplyOpen] = useState(false);

  const view = useQuery({ queryKey: ['admin', 'config'], queryFn: adminApi.config, retry: false });

  const previewMutation = useMutation({
    mutationFn: (changes: Record<string, number>) => adminApi.previewConfig(changes),
    onSuccess: (data) => setPreview(data),
  });
  const apply = useMutation({
    mutationFn: ({ changes, rationale }: { changes: Record<string, number>; rationale: string }) =>
      adminApi.applyConfig(changes, rationale),
    onSuccess: () => {
      setApplyOpen(false);
      setPreview(null);
      setDraft({});
      void qc.invalidateQueries({ queryKey: ['admin', 'config'] });
    },
  });

  if (view.isLoading) return <PageLoader />;
  if (view.isError || !view.data) {
    return <ErrorState message={localizeError(view.error, t)} error={view.error} onRetry={() => void view.refetch()} />;
  }
  const { config, editable_paths: paths, versions, version } = view.data;

  const changes: Record<string, number> = {};
  const invalid: string[] = [];
  for (const path of paths) {
    const text = draft[path];
    if (text === undefined || text === toInput(path, read(config, path))) continue;
    const value = fromInput(path, text);
    if (value === null) invalid.push(path);
    else changes[path] = value;
  }
  const hasChanges = Object.keys(changes).length > 0;

  function edit(path: string, value: string): void {
    setDraft((d) => ({ ...d, [path]: value }));
    setPreview(null);
    previewMutation.reset();
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-h1 text-fg">{t('admin:config.title')}</h1>
        <p className="mt-1 text-body-sm text-fg-muted">{t('admin:config.subtitle', { version })}</p>
      </div>

      <Card className="space-y-4">
        <h2 className="text-h3 text-fg">{t('admin:config.editable')}</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {paths.map((path) => {
            const id = `cfg-${path.replace(/\./g, '-')}`;
            const current = read(config, path);
            return (
              <div key={path} className="space-y-1">
                <label htmlFor={id} className="block text-label text-fg-secondary">
                  {t(`admin:config.key.${path}`, { defaultValue: path })}
                </label>
                <Input
                  id={id}
                  inputMode="decimal"
                  value={draft[path] ?? toInput(path, current)}
                  invalid={invalid.includes(path)}
                  aria-describedby={`${id}-hint`}
                  onChange={(e) => edit(path, e.target.value)}
                />
                <p id={`${id}-hint`} className="text-body-sm text-fg-muted">
                  {t('admin:config.live', { value: display(path, current, t) })}
                </p>
              </div>
            );
          })}
        </div>
        {invalid.length > 0 && <Alert tone="danger">{t('admin:config.invalid')}</Alert>}
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            disabled={!hasChanges || invalid.length > 0}
            loading={previewMutation.isPending}
            onClick={() => previewMutation.mutate(changes)}
          >
            {t('admin:config.preview')}
          </Button>
          {Object.keys(draft).length > 0 && (
            <Button variant="tertiary" onClick={() => { setDraft({}); setPreview(null); }}>
              {t('admin:config.discard')}
            </Button>
          )}
        </div>
        {previewMutation.isError && <Alert tone="danger">{localizeError(previewMutation.error, t)}</Alert>}
      </Card>

      {preview && (
        <Card className="space-y-4">
          <h2 className="text-h3 text-fg">{t('admin:config.diffTitle')}</h2>
          <ul className="space-y-1">
            {preview.changes.map((c) => (
              <li key={c.path} className="text-body text-fg">
                {t(`admin:config.key.${c.path}`, { defaultValue: c.path })}: {display(c.path, c.before, t)} →{' '}
                <strong>{display(c.path, c.after, t)}</strong>
              </li>
            ))}
          </ul>
          {preview.changes.some((c) => c.path.startsWith('commission.')) && (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left text-body-sm">
                <caption className="pb-2 text-left text-label text-fg-secondary">{t('admin:config.effect')}</caption>
                <thead>
                  <tr className="border-b border-line-strong text-fg-secondary">
                    <th scope="col" className="py-2 pr-3">{t('admin:config.col.price')}</th>
                    <th scope="col" className="py-2 pr-3">{t('admin:config.col.before')}</th>
                    <th scope="col" className="py-2">{t('admin:config.col.after')}</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.commission_samples.map((s) => (
                    <tr key={s.agreed_price_kes} className="border-b border-line">
                      <th scope="row" className="fk-numeric py-2 pr-3 font-normal">{formatKes(s.agreed_price_kes)}</th>
                      <td className="fk-numeric py-2 pr-3">{formatKes(s.before_kes)}</td>
                      <td className="fk-numeric py-2 font-semibold">{formatKes(s.after_kes)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <Button onClick={() => { apply.reset(); setApplyOpen(true); }}>{t('admin:config.apply')}</Button>
        </Card>
      )}

      <Card className="space-y-2">
        <h2 className="text-h3 text-fg">{t('admin:config.readOnly')}</h2>
        <p className="text-body-sm text-fg-muted">{t('admin:config.readOnlyHint')}</p>
        {(['value_bands', 'high_value_threshold_kes', 'role_permissions', 'verification_requirements'] as const).map((key) => (
          <details key={key} className="rounded-md border border-line px-3 py-2">
            <summary className="cursor-pointer text-body text-fg">{t(`admin:config.section.${key}`)}</summary>
            <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-caption text-fg-secondary">
              {JSON.stringify(config[key], null, 2)}
            </pre>
          </details>
        ))}
      </Card>

      <Card className="space-y-2">
        <h2 className="text-h3 text-fg">{t('admin:config.history')}</h2>
        <ul className="space-y-3">
          {versions.map((v) => (
            <li key={v.version} className="text-body-sm">
              <span className="font-semibold text-fg">{t('admin:config.versionLabel', { version: v.version })}</span>
              <span className="block text-fg-secondary">{v.rationale}</span>
              <span className="block text-fg-muted">
                {[v.changed_by_name || t('admin:config.system'), formatDateTime(v.created_at)].join(' · ')}
              </span>
            </li>
          ))}
        </ul>
      </Card>

      <AdminActionDialog
        open={applyOpen}
        onClose={() => setApplyOpen(false)}
        title={t('admin:config.applyTitle')}
        restatement={t('admin:config.applyRestate', { count: preview?.changes.length ?? 0, version: version + 1 })}
        confirmLabel={t('admin:config.applyConfirm')}
        destructive={false}
        pending={apply.isPending}
        error={apply.error}
        onConfirm={({ reason }) => apply.mutate({ changes, rationale: reason })}
      />
    </div>
  );
}
