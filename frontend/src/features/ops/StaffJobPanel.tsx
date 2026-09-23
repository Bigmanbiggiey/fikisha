import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { Modal } from '@/components/Modal';
import { disputesApi } from '@/features/incidents/incidentsApi';
import { jobReference } from '@/features/jobs/jobHelpers';
import { jobsApi } from '@/features/jobs/jobsApi';
import type { Job } from '@/features/jobs/types';
import { localizeError } from '@/services/errorMessage';

import { notesQueryKey, opsApi } from './opsApi';
import type { ContactParty, RevealedContacts } from './types';

export const textareaClass =
  'min-h-[72px] w-full rounded-md border border-line-strong bg-surface-input px-3 py-2 text-body text-fg';

const CONTACT_ORDER: ContactParty[] = ['business', 'pickup', 'destination', 'recipient', 'operator', 'driver'];

/**
 * The Job Detail staff section (P3 §18.2, Design Phase 6 Increment 8) —
 * rendered in place of the Business/Operator next-action card when the
 * viewer is Fikisha staff. Founder-approved interventions only:
 * operational note, audited contact reveal, open an incident, and cancel
 * with a reason. Cancel above STANDARD is Platform-Admin-only; for an Ops
 * Officer the control is *replaced* by the reason it isn't available,
 * mirroring the server's `AdminCancelBandAuthorised` guard (the server is
 * the enforcement, this is UX). Reassign / force-fail / flag are deferred.
 */
export function StaffJobPanel({ job, isPlatformAdmin }: { job: Job; isPlatformAdmin: boolean }): JSX.Element {
  const { t } = useTranslation(['ops', 'jobs', 'errors']);
  const qc = useQueryClient();
  const ref = jobReference(job.id);

  const [noteText, setNoteText] = useState('');
  const [noteSent, setNoteSent] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [cancelReason, setCancelReason] = useState('');
  const [eventsOpen, setEventsOpen] = useState(false);

  const addNote = useMutation({
    mutationFn: () => opsApi.addNote(job.id, noteText.trim()),
    onSuccess: () => {
      setNoteText('');
      setNoteSent(true);
      void qc.invalidateQueries({ queryKey: notesQueryKey(job.id) });
      void qc.invalidateQueries({ queryKey: ['job-events', job.id] });
    },
  });

  const contacts = useMutation({ mutationFn: () => opsApi.revealContacts(job.id) });

  const cancel = useMutation({
    mutationFn: () =>
      jobsApi.cancel(job.id, { reason_code: 'ADMIN_ACTION', reason_text: cancelReason.trim() }, crypto.randomUUID()),
    onSuccess: () => {
      setCancelOpen(false);
      void qc.invalidateQueries({ queryKey: ['jobs', job.id] });
      void qc.invalidateQueries({ queryKey: ['jobs'] });
    },
  });

  const disputes = useQuery({
    queryKey: ['disputes', job.id],
    queryFn: () => disputesApi.listForJob(job.id),
    enabled: job.status === 'DISPUTED',
    retry: false,
  });
  const dispute = disputes.data?.data[0];

  const events = useQuery({
    queryKey: ['job-events', job.id],
    queryFn: () => opsApi.events(job.id),
    enabled: eventsOpen,
    retry: false,
  });

  const canCancel = job.next_allowed_statuses.includes('CANCELLED');
  const aboveStandard = !!job.value_band && job.value_band !== 'STANDARD' && job.status !== 'DRAFT';
  const cancelNeedsPlatformAdmin = aboveStandard && !isPlatformAdmin;

  return (
    <Card className="space-y-5">
      <h2 className="text-h3 text-fg">{t('ops:staff.title')}</h2>

      {/* Operational note */}
      <section className="space-y-2">
        <label htmlFor="staff-note" className="block text-label text-fg-secondary">
          {t('ops:staff.note')}
        </label>
        <textarea
          id="staff-note"
          aria-describedby="staff-note-hint"
          value={noteText}
          maxLength={2000}
          onChange={(e) => {
            setNoteText(e.target.value);
            setNoteSent(false);
          }}
          className={textareaClass}
        />
        <p id="staff-note-hint" className="text-body-sm text-fg-muted">
          {t('ops:staff.noteHint')}
        </p>
        <Button
          size="compact"
          variant="secondary"
          disabled={!noteText.trim()}
          loading={addNote.isPending}
          onClick={() => addNote.mutate()}
        >
          {t('ops:staff.sendNote')}
        </Button>
        {noteSent && (
          <p role="status" className="text-body-sm text-fg-secondary">
            {t('ops:staff.noteSent')}
          </p>
        )}
        {addNote.isError && <Alert tone="danger">{localizeError(addNote.error, t)}</Alert>}
      </section>

      {/* Contact the parties — every reveal is audited server-side */}
      <section className="space-y-2 border-t border-line pt-4">
        <h3 className="text-label text-fg-secondary">{t('ops:staff.contacts')}</h3>
        {contacts.data ? (
          <ContactList contacts={contacts.data} />
        ) : (
          <>
            <p className="text-body-sm text-fg-muted">{t('ops:staff.contactsLogged')}</p>
            <Button
              size="compact"
              variant="secondary"
              loading={contacts.isPending}
              onClick={() => contacts.mutate()}
            >
              {t('ops:staff.showContacts')}
            </Button>
          </>
        )}
        {contacts.isError && <Alert tone="danger">{localizeError(contacts.error, t)}</Alert>}
      </section>

      {/* Incident / dispute */}
      <section className="flex flex-wrap gap-4 border-t border-line pt-4 text-body-sm">
        {job.status !== 'DRAFT' && (
          <Link to={`/jobs/${job.id}/report-issue`} className="text-action-secondary-text underline">
            {t('ops:staff.openIncident')}
          </Link>
        )}
        {dispute && (
          <Link to={`/disputes/${dispute.id}`} className="text-action-secondary-text underline">
            {t('ops:staff.viewDispute')}
          </Link>
        )}
      </section>

      {/* Cancel — band-limited for an Ops Officer */}
      {canCancel && (
        <section className="border-t border-line pt-4">
          {cancelNeedsPlatformAdmin ? (
            <Alert tone="info">{t('ops:staff.needsPlatformAdmin')}</Alert>
          ) : (
            <Button variant="destructive" size="compact" onClick={() => setCancelOpen(true)}>
              {t('ops:staff.cancel')}
            </Button>
          )}
        </section>
      )}

      {/* Staff event log (§14 raw-event drawer) */}
      <section className="border-t border-line pt-4">
        <Button
          variant="tertiary"
          size="compact"
          aria-expanded={eventsOpen}
          aria-controls="staff-event-log"
          onClick={() => setEventsOpen((v) => !v)}
        >
          {eventsOpen ? t('ops:staff.hideEvents') : t('ops:staff.showEvents')}
        </Button>
        {eventsOpen && (
          <ol id="staff-event-log" aria-label={t('ops:staff.events')} className="mt-3 space-y-2">
            {(events.data?.data ?? []).map((e) => (
              <li key={e.seq} className="rounded-md bg-surface-sunken px-3 py-2 text-body-sm">
                <span className="fk-numeric text-fg-muted">#{e.seq}</span>{' '}
                <span className="font-semibold text-fg">{e.type}</span>
                {e.from_status && e.to_status && (
                  <span className="text-fg-secondary">
                    {' '}
                    · {e.from_status} → {e.to_status}
                  </span>
                )}
                <span className="text-fg-muted">
                  {' '}
                  · {e.actor_role || '—'} · {new Date(e.server_time).toLocaleString()}
                </span>
                {e.note && <p className="mt-1 whitespace-pre-line text-fg">{e.note}</p>}
              </li>
            ))}
          </ol>
        )}
        {events.isError && <Alert tone="danger">{localizeError(events.error, t)}</Alert>}
      </section>

      <Modal
        open={cancelOpen}
        onClose={() => setCancelOpen(false)}
        title={t('ops:staff.cancelTitle', { ref })}
        footer={
          <>
            <Button variant="secondary" onClick={() => setCancelOpen(false)}>
              {t('ops:staff.keep')}
            </Button>
            <Button
              variant="destructive"
              disabled={!cancelReason.trim()}
              loading={cancel.isPending}
              onClick={() => cancel.mutate()}
            >
              {t('ops:staff.confirmCancel')}
            </Button>
          </>
        }
      >
        <div className="space-y-2">
          <label htmlFor="staff-cancel-reason" className="block text-label text-fg-secondary">
            {t('ops:staff.cancelReason')}
          </label>
          <textarea
            id="staff-cancel-reason"
            aria-describedby="staff-cancel-hint"
            value={cancelReason}
            maxLength={2000}
            onChange={(e) => setCancelReason(e.target.value)}
            className={textareaClass}
          />
          <p id="staff-cancel-hint" className="text-body-sm text-fg-muted">
            {t('ops:staff.cancelHint')}
          </p>
          {cancel.isError && <Alert tone="danger">{localizeError(cancel.error, t)}</Alert>}
        </div>
      </Modal>
    </Card>
  );
}

function ContactList({ contacts }: { contacts: RevealedContacts }): JSX.Element {
  const { t } = useTranslation('ops');
  return (
    <dl className="space-y-2">
      {CONTACT_ORDER.filter((party) => contacts.contacts[party]).map((party) => {
        const c = contacts.contacts[party]!;
        const digits = c.phone.replace(/[^0-9]/g, '');
        return (
          <div key={party} className="flex flex-wrap items-baseline justify-between gap-2">
            <dt className="text-body-sm text-fg-muted">{t(`staff.party.${party}`)}</dt>
            <dd className="text-body text-fg">
              {c.name || '—'}
              {c.phone ? (
                <>
                  {' · '}
                  <a href={`tel:${c.phone}`} className="text-action-secondary-text underline">
                    {c.phone}
                  </a>
                  {' · '}
                  <a
                    href={`https://wa.me/${digits}`}
                    target="_blank"
                    rel="noreferrer"
                    className="text-action-secondary-text underline"
                  >
                    {t('staff.whatsapp')}
                  </a>
                </>
              ) : (
                <span className="text-fg-muted"> · {t('staff.noPhone')}</span>
              )}
            </dd>
          </div>
        );
      })}
    </dl>
  );
}
