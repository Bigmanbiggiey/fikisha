import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { Card } from '@/components/Card';
import { formatDateTime } from '@/services/datetime';

import { adminApi } from './adminApi';

/**
 * A business's track record for Fikisha staff (trust plan A8), in separate
 * sections so an open report never reads as a finding, a closure never as
 * fault, and "no fault" never as an unfounded report. Information only:
 * standing changes only through the suspend / reinstate controls.
 */
export function BusinessRecordCard({ businessId }: { businessId: string }): JSX.Element | null {
  const { t } = useTranslation(['admin', 'incidents']);
  const q = useQuery({
    queryKey: ['admin', 'business-record', businessId],
    queryFn: () => adminApi.businessRecord(businessId),
    retry: false,
  });
  if (!q.data) return null;
  const r = q.data;
  const type = (k: string): string => t(`incidents:report.type.${k}`);
  return (
    <Card className="space-y-4">
      <h2 className="text-h3 text-fg">{t('admin:record.title')}</h2>
      <p className="text-body text-fg">
        {r.rating.average === null
          ? t('admin:record.ratingNone', { count: r.rating.count })
          : t('admin:record.rating', { average: r.rating.average, count: r.rating.count })}
      </p>

      <Section title={t('admin:record.openReports')} empty={r.open_reports.length === 0}>
        {r.open_reports.map((i) => (
          <li key={i.id}>
            <Link to={`/incidents/${i.id}`} className="text-action-secondary-text underline">
              {type(i.type)}
            </Link>{' '}
            · {formatDateTime(i.created_at)}
          </li>
        ))}
      </Section>

      <Section title={t('admin:record.closed')} empty={r.closed_incidents.length === 0}>
        {r.closed_incidents.map((i) => (
          <li key={i.id}>
            {type(i.type)} ·{' '}
            {i.reason_code ? t(`incidents:detail.closure.reason.${i.reason_code}`) : t('admin:record.noClosure')}
          </li>
        ))}
      </Section>

      <Section title={t('admin:record.findings')} empty={r.findings_against.length === 0}>
        {r.findings_against.map((f) => (
          <li key={f.id} className={f.current ? 'text-fg' : 'text-fg-muted line-through'}>
            {type(f.type)} · {f.reason}
            {!f.current && ` (${t('admin:record.superseded')})`}
          </li>
        ))}
      </Section>

      <Section title={t('admin:record.unfounded')} empty={r.unfounded_reports.length === 0}>
        {r.unfounded_reports.map((u) => (
          <li key={u.incident_id}>
            {type(u.type)} · {u.reason}
          </li>
        ))}
      </Section>

      <Section title={t('admin:record.flags')} empty={r.cancellation_flags.length === 0}>
        {r.cancellation_flags.map((f) => (
          <li key={f.id}>
            {t('admin:record.flagRow', { count: f.count })} · {t(`admin:record.flagStatus.${f.status}`)} ·{' '}
            {formatDateTime(f.created_at)}
          </li>
        ))}
      </Section>
    </Card>
  );
}

function Section({ title, empty, children }: { title: string; empty: boolean; children: React.ReactNode }): JSX.Element {
  const { t } = useTranslation('admin');
  return (
    <section className="space-y-1">
      <h3 className="text-label text-fg-secondary">{title}</h3>
      {empty ? (
        <p className="text-body-sm text-fg-muted">{t('admin:record.none')}</p>
      ) : (
        <ul className="space-y-1 text-body-sm text-fg">{children}</ul>
      )}
    </section>
  );
}
