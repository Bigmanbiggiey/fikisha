import { useQuery } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Card } from '@/components/Card';
import { JobStatusHeader } from '@/components/JobStatusHeader';
import { NextActionCard } from '@/components/NextActionCard';
import { cn } from '@/components/cn';
import { Icon } from '@/design/Icon';
import { vehiclesApi } from '@/features/vehicles/vehiclesApi';

import { mapsHref, telHref, whatsappHref } from './contactLinks';
import { jobReference } from './jobHelpers';
import type { Job } from './types';

/**
 * The driver's "Current job" (Design Phase 7 P-03, F-03; P3 §10.1): one
 * screen that says what to do next, in the §10.1 order: reference + a
 * driver-voiced state line, the one large action, the sender and receiver
 * contacts (current step first) with Call / WhatsApp / map hand-off, cargo
 * and vehicle, a compact 3-step progress, Report an issue, and the full job
 * detail behind a disclosure.
 *
 * The action itself is passed in (`action`), so the lifecycle mutations and
 * `operatorNextAction` stay in one place (JobDetailPage). Rendering only.
 */
export function DriverJobView({
  job,
  action,
  actionError,
  fullDetail,
}: {
  job: Job;
  /** the one next action (JobDetailPage's operator action section) */
  action: ReactNode;
  actionError?: ReactNode;
  /** the existing route / price / timeline cards, shown on demand */
  fullDetail: ReactNode;
}): JSX.Element {
  const { t } = useTranslation(['jobs', 'incidents']);

  // The plate and class come from the vehicle itself; a group driver may
  // read their group's vehicles. If the read is refused, leave the line out.
  const vehicle = useQuery({
    queryKey: ['vehicles', job.assigned_vehicle_id],
    queryFn: () => vehiclesApi.get(job.assigned_vehicle_id!),
    enabled: !!job.assigned_vehicle_id,
    retry: false,
    staleTime: Infinity,
  });

  const pickedUp = !!job.timestamps.picked_up_at;
  // Name and phone come as a pair from one source, so "Call <name>" never
  // dials someone else: the recipient if either recipient field is set,
  // otherwise the drop-off location's own contact.
  const receiverContact =
    job.recipient_name || job.recipient_phone
      ? { name: job.recipient_name, phone: job.recipient_phone }
      : { name: job.destination_location?.contact_name, phone: job.destination_location?.contact_phone };
  const sender = (
    <ContactCard
      key="sender"
      title={t('jobs:driver.pickupCard')}
      address={job.pickup_location?.address_text}
      name={job.pickup_location?.contact_name}
      phone={job.pickup_location?.contact_phone}
      mapHref={mapsHref(job.pickup_location)}
      goLabel={t('jobs:driver.goPickup')}
    />
  );
  const receiver = (
    <ContactCard
      key="receiver"
      title={t('jobs:driver.dropoffCard')}
      address={job.destination_location?.address_text}
      name={receiverContact.name}
      phone={receiverContact.phone}
      mapHref={mapsHref(job.destination_location)}
      goLabel={t('jobs:driver.goDropoff')}
    />
  );

  return (
    <div className="mx-auto max-w-[640px] space-y-4">
      <div className="space-y-2">
        <h1 className="fk-numeric text-h2 text-fg">{t('jobs:driver.jobRef', { ref: jobReference(job.id) })}</h1>
        <JobStatusHeader
          state={job.status}
          stateLabel={t(`jobs:status.${job.status}`)}
          line={t(`jobs:statusLine.${job.status}_DRIVER`)}
        />
      </div>

      {job.status === 'DISPUTED' && <Alert tone="warning">{t('jobs:driver.onHold')}</Alert>}
      {job.status === 'DELIVERED' ? (
        <NextActionCard driver emptyLabel={t('jobs:driver.deliveryRecorded')} />
      ) : (
        action
      )}
      {actionError}

      {/* The contact for the current step comes first: the sender until
          the goods are collected, then the receiver. */}
      <div className="space-y-3">{pickedUp ? [receiver, sender] : [sender, receiver]}</div>

      <Card>
        <dl className="space-y-2 text-body">
          <div>
            <dt className="text-label text-fg-secondary">{t('jobs:detail.cargo')}</dt>
            <dd className="text-fg">{job.cargo?.description || '—'}</dd>
            {job.cargo?.handling_flags && job.cargo.handling_flags.length > 0 && (
              <dd className="text-body-sm text-fg-secondary">{job.cargo.handling_flags.join(' · ')}</dd>
            )}
          </div>
          {vehicle.data && (
            <div>
              <dt className="text-label text-fg-secondary">{t('jobs:driver.vehicle')}</dt>
              <dd className="fk-numeric text-fg">
                {vehicle.data.registration} · {vehicle.data.vehicle_class}
              </dd>
            </div>
          )}
        </dl>
      </Card>

      <DriverProgress job={job} />

      <div>
        <Link to={`/jobs/${job.id}/report-issue`} className="text-body text-action-secondary-text underline">
          {t('incidents:report.entryLink')}
        </Link>
      </div>

      <details className="rounded-md border border-line bg-surface-card">
        <summary className="flex min-h-target cursor-pointer items-center px-4 text-body text-fg">
          {t('jobs:driver.fullDetail')}
        </summary>
        <div className="space-y-4 border-t border-line p-4">{fullDetail}</div>
      </details>
    </div>
  );
}

function ContactCard({
  title,
  address,
  name,
  phone,
  mapHref,
  goLabel,
}: {
  title: string;
  address: string | null | undefined;
  name: string | null | undefined;
  phone: string | null | undefined;
  mapHref: string | null;
  goLabel: string;
}): JSX.Element {
  const { t } = useTranslation('jobs');
  const tel = telHref(phone);
  const wa = whatsappHref(phone);
  const who = name || t('jobs:driver.contactFallback');
  const linkClass =
    'inline-flex min-h-target items-center gap-1 rounded-md border border-line-strong px-3 text-body text-action-secondary-text';

  return (
    <Card>
      <h2 className="text-label text-fg-secondary">{title}</h2>
      <p className="mt-1 text-body text-fg">{address || '—'}</p>
      <p className="mt-1 text-body text-fg">
        {name || <span className="text-fg-muted">{t('jobs:driver.noName')}</span>}
        {phone ? (
          <span className="fk-numeric select-text text-fg-secondary"> · {phone}</span>
        ) : (
          <span className="text-fg-muted"> · {t('jobs:driver.noPhone')}</span>
        )}
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        {tel && (
          <a href={tel} className={linkClass} aria-label={t('jobs:driver.callWho', { who })}>
            <Icon name="phone" size={18} />
            {t('jobs:driver.call')}
          </a>
        )}
        {wa && (
          <a
            href={wa}
            target="_blank"
            rel="noreferrer"
            className={linkClass}
            aria-label={t('jobs:driver.whatsappWho', { who })}
          >
            <Icon name="chat" size={18} />
            {t('jobs:driver.whatsapp')}
          </a>
        )}
        {mapHref && (
          <a href={mapHref} target="_blank" rel="noreferrer" className={linkClass}>
            <Icon name="pin" size={18} />
            {goLabel}
          </a>
        )}
      </div>
    </Card>
  );
}

type StepNode = 'done' | 'current' | 'upcoming';

/** "Pickup → Transit → Delivery" (P3 §10.1), an ordered list with
 * `aria-current` on the current step. A DISPUTED job shows where it
 * stopped, from its timestamps. */
function DriverProgress({ job }: { job: Job }): JSX.Element {
  const { t } = useTranslation('jobs');
  const current = progressIndex(job);
  const steps = (['pickup', 'transit', 'delivery'] as const).map((key, i): [string, StepNode] => [
    t(`jobs:driver.progress.${key}`),
    i < current ? 'done' : i === current ? 'current' : 'upcoming',
  ]);

  return (
    <Card>
      <h2 className="text-label text-fg-secondary">{t('jobs:driver.progress.title')}</h2>
      <ol className="mt-2 flex flex-wrap gap-x-4 gap-y-2">
        {steps.map(([label, node]) => (
          <li
            key={label}
            aria-current={node === 'current' ? 'step' : undefined}
            className={cn(
              'flex items-center gap-1 text-body',
              node === 'upcoming' ? 'text-fg-muted' : 'text-fg',
              node === 'current' && 'font-semibold',
            )}
          >
            <Icon
              name={node === 'done' ? 'check' : node === 'current' ? 'dotCurrent' : 'circle'}
              size={18}
              title={t(`jobs:driver.progress.${node}`)}
            />
            {label}
          </li>
        ))}
      </ol>
    </Card>
  );
}

/** 0 = pickup, 1 = transit, 2 = delivery, 3 = all done. */
function progressIndex(job: Job): number {
  switch (job.status) {
    case 'ASSIGNED':
    case 'AT_PICKUP':
      return 0;
    case 'PICKED_UP':
    case 'IN_TRANSIT':
      return 1;
    case 'AT_DESTINATION':
      return 2;
    case 'DELIVERED':
      return 3;
    default:
      // DISPUTED (frozen): how far it got, from the timestamps.
      return job.timestamps.delivered_at ? 3 : job.timestamps.picked_up_at ? 1 : 0;
  }
}
