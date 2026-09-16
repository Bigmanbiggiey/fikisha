import { StatusBadge } from './StatusBadge';
import { cn } from './cn';
import { entryStatusIcon, entryStatusTone } from '@/features/negotiation/negotiationHelpers';

/**
 * OfferCard — one negotiation entry (`design-phase-3-wireframes.md` §8.1's
 * offer/counter card): proposer, amount, timestamp, status, optional note.
 * Presentational only — the caller resolves the proposer name and status
 * label (translated) and passes them in.
 */
export function OfferCard({
  you,
  proposerName,
  amountLabel,
  time,
  note,
  statusLabel,
  statusKey,
}: {
  /** Right-aligns the card and uses the "you" treatment, matching the
   * wireframe's chat-style layout. */
  you: boolean;
  proposerName: string;
  /** Pre-formatted (`formatKes`) — `null` for a note-only entry (DECLINE). */
  amountLabel: string | null;
  time: string;
  note?: string;
  /** Translated display text for the status chip. */
  statusLabel: string;
  /** Untranslated key (`current`/`countered`/`expired`/`accepted`/`declined`)
   * driving the chip's tone/icon. */
  statusKey: string;
}): JSX.Element {
  return (
    <li className={cn('flex flex-col gap-1', you ? 'items-end' : 'items-start')}>
      <div className="flex items-baseline gap-2 text-caption text-fg-muted">
        <span>{proposerName}</span>
        <span>{time}</span>
      </div>
      <div
        className={cn(
          'max-w-[85%] rounded-md border border-line px-3 py-2',
          you ? 'bg-surface-brand-tint' : 'bg-surface-card',
        )}
      >
        {amountLabel && (
          <p className="fk-numeric text-body font-semibold text-fg">{amountLabel}</p>
        )}
        {note && <p className="mt-1 text-body-sm text-fg-secondary">{note}</p>}
        <div className="mt-1">
          <StatusBadge
            tone={entryStatusTone(statusKey)}
            icon={entryStatusIcon(statusKey)}
            label={statusLabel}
          />
        </div>
      </div>
    </li>
  );
}
