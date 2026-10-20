import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { Select } from '@/components/Select';
import { Textarea } from '@/components/Textarea';
import { localizeError } from '@/services/errorMessage';

import { incidentsApi } from './incidentsApi';
import {
  FINDING_OUTCOMES,
  type FindingOutcome,
  type FindingPartyKind,
  type Incident,
  type IncidentFinding,
} from './types';

const MIN_REASON = 10;

function FindingLine({ finding }: { finding: IncidentFinding }): JSX.Element {
  const { t } = useTranslation('incidents');
  const parties = finding.parties.map((p) => t(`finding.party.${p}`)).join(', ');
  return (
    <p className="text-body text-fg">
      {finding.outcome === 'AT_FAULT'
        ? t('finding.atFault', { parties })
        : t(`finding.outcome.${finding.outcome}`)}
    </p>
  );
}

/**
 * Fikisha's finding on an incident (trust-and-disputes plan A2, A3). Every
 * reader sees the current finding; staff record or replace it, see why and
 * the earlier ones; a Platform Admin can mark a closed no-fault report
 * unfounded. Never a legal ruling.
 */
export function FindingPanel({
  incident,
  isStaff,
  isPlatformAdmin,
  onChanged,
}: {
  incident: Incident;
  isStaff: boolean;
  isPlatformAdmin: boolean;
  onChanged: () => void;
}): JSX.Element | null {
  const { t } = useTranslation(['incidents', 'errors']);
  const [outcome, setOutcome] = useState<FindingOutcome | ''>('');
  const [parties, setParties] = useState<FindingPartyKind[]>([]);
  const [reason, setReason] = useState('');
  const [unfoundedReason, setUnfoundedReason] = useState('');

  const record = useMutation({
    mutationFn: () =>
      incidentsApi.recordFinding(incident.id, {
        outcome: outcome as FindingOutcome,
        parties: outcome === 'AT_FAULT' ? parties : [],
        reason,
      }),
    onSuccess: () => {
      setOutcome('');
      setParties([]);
      setReason('');
      onChanged();
    },
  });
  const unfounded = useMutation({
    mutationFn: () => incidentsApi.markUnfounded(incident.id, unfoundedReason),
    onSuccess: () => {
      setUnfoundedReason('');
      onChanged();
    },
  });

  const current = incident.finding;
  if (!current && !isStaff) return null;
  const earlier = (incident.finding_history ?? []).filter((f) => f.id !== current?.id);
  const candidates = incident.finding_candidates ?? [];
  const canSave =
    outcome !== '' &&
    reason.trim().length >= MIN_REASON &&
    (outcome !== 'AT_FAULT' || parties.length > 0);
  const canMarkUnfounded =
    isPlatformAdmin &&
    incident.status === 'RESOLVED' &&
    current?.outcome === 'NO_FAULT' &&
    !incident.unfounded;

  return (
    <Card className="space-y-3">
      <h2 className="text-label text-fg-secondary">{t('finding.title')}</h2>
      {current ? (
        <div className="space-y-1">
          <FindingLine finding={current} />
          {current.reason && (
            <p className="text-body-sm text-fg-secondary">
              {t('finding.reason')}: {current.reason}
            </p>
          )}
        </div>
      ) : (
        <p className="text-body-sm text-fg-muted">{t('finding.none')}</p>
      )}
      <p className="text-caption text-fg-muted">{t('finding.disclaimer')}</p>

      {isStaff && earlier.length > 0 && (
        <div className="space-y-1">
          <h3 className="text-label text-fg-secondary">{t('finding.history')}</h3>
          <ul className="space-y-1">
            {earlier.map((f) => (
              <li key={f.id} className="text-body-sm text-fg-secondary">
                {t('finding.replaced')}: <FindingLine finding={f} />
              </li>
            ))}
          </ul>
        </div>
      )}

      {incident.unfounded && (
        <Alert tone="info">{t('finding.unfounded.recorded')}</Alert>
      )}

      {isStaff && (
        <div className="space-y-2 border-t border-line pt-3">
          <h3 className="text-label text-fg">
            {current ? t('finding.replace') : t('finding.record')}
          </h3>
          <label htmlFor="finding-outcome" className="block text-body-sm text-fg-secondary">
            {t('finding.outcomeLabel')}
          </label>
          <Select
            id="finding-outcome"
            value={outcome}
            onChange={(e) => setOutcome(e.target.value as FindingOutcome | '')}
          >
            <option value="">{t('finding.choose')}</option>
            {FINDING_OUTCOMES.map((o) => (
              <option key={o} value={o}>
                {t(`finding.outcome.${o}`)}
              </option>
            ))}
          </Select>
          {outcome === 'AT_FAULT' && (
            <fieldset className="space-y-2">
              <legend className="text-body-sm text-fg-secondary">{t('finding.partiesLabel')}</legend>
              {candidates.map((kind) => (
                <label key={kind} className="flex items-center gap-2 text-body-sm text-fg">
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-line-strong"
                    checked={parties.includes(kind)}
                    onChange={(e) =>
                      setParties(
                        e.target.checked ? [...parties, kind] : parties.filter((p) => p !== kind),
                      )
                    }
                  />
                  {t(`finding.party.${kind}`)}
                </label>
              ))}
              {candidates.includes('GROUP') && (
                <p className="text-caption text-fg-muted">{t('finding.groupHint')}</p>
              )}
            </fieldset>
          )}
          <Textarea
            aria-label={t('finding.reasonLabel')}
            placeholder={t('finding.reasonLabel')}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
          <Button
            variant="secondary"
            disabled={!canSave}
            loading={record.isPending}
            onClick={() => record.mutate()}
          >
            {t('finding.submit')}
          </Button>
          {record.isError && <Alert tone="danger">{localizeError(record.error, t)}</Alert>}
        </div>
      )}

      {canMarkUnfounded && (
        <div className="space-y-2 border-t border-line pt-3">
          <h3 className="text-label text-fg">{t('finding.unfounded.title')}</h3>
          <p className="text-caption text-fg-muted">{t('finding.unfounded.explain')}</p>
          <Textarea
            aria-label={t('finding.unfounded.reason')}
            placeholder={t('finding.unfounded.reason')}
            value={unfoundedReason}
            onChange={(e) => setUnfoundedReason(e.target.value)}
          />
          <Button
            variant="secondary"
            disabled={unfoundedReason.trim().length < MIN_REASON}
            loading={unfounded.isPending}
            onClick={() => unfounded.mutate()}
          >
            {t('finding.unfounded.submit')}
          </Button>
          {unfounded.isError && <Alert tone="danger">{localizeError(unfounded.error, t)}</Alert>}
        </div>
      )}
    </Card>
  );
}
