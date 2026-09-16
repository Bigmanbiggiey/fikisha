import { OfferCard } from './OfferCard';
import { formatKes } from '@/features/jobs/money';
import { entryStatusLabel, proposerOf } from '@/features/negotiation/negotiationHelpers';
import type { NegotiationEntry } from '@/features/negotiation/types';

/**
 * NegotiationThread — the ordered offer/counter history
 * (`design-phase-3-wireframes.md` §8.1). Presentational: the caller
 * supplies already-resolved translations via `labelFor`/`statusLabelFor`
 * so this component (and `OfferCard`) stay free of `useTranslation`,
 * matching every other presentational primitive in this directory.
 */
export function NegotiationThread({
  entries,
  viewerRole,
  operatorDisplayName,
  youLabel,
  adminLabel,
  operatorFallbackLabel,
  statusLabelFor,
  timeFor,
}: {
  entries: NegotiationEntry[];
  viewerRole: 'BUSINESS' | 'OPERATOR';
  operatorDisplayName: string | null;
  youLabel: string;
  adminLabel: string;
  operatorFallbackLabel: string;
  /** Translate a status key (`current`/`countered`/`expired`/`accepted`/`declined`). */
  statusLabelFor: (statusKey: string) => string;
  timeFor: (iso: string) => string;
}): JSX.Element {
  return (
    <ol aria-live="polite" className="space-y-3">
      {entries.map((entry) => {
        const proposer = proposerOf(entry, viewerRole, operatorDisplayName);
        const proposerName =
          proposer.kind === 'you'
            ? youLabel
            : proposer.kind === 'admin'
              ? adminLabel
              : proposer.name || operatorFallbackLabel;
        const statusKey = entryStatusLabel(entry);
        return (
          <OfferCard
            key={entry.id}
            you={proposer.kind === 'you'}
            proposerName={proposerName}
            amountLabel={entry.amount_kes != null ? formatKes(entry.amount_kes) : null}
            time={timeFor(entry.created_at)}
            note={entry.note || undefined}
            statusLabel={statusLabelFor(statusKey)}
            statusKey={statusKey}
          />
        );
      })}
    </ol>
  );
}
