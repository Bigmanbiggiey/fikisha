import type { TFunction } from 'i18next';

import { formatKes } from '@/features/jobs/money';

import type { MessageItem } from './types';

/**
 * The two lines of an inbox row, in the reader's language. Offers are
 * worded from the reader's side ("You offered" / "A. Otieno offered"); the
 * note stored on an offer is not shown, since it can be system text.
 */
export function messageLines(item: MessageItem, t: TFunction): { title: string; body: string } {
  const kind = t(`messages:kind.${item.kind}`);
  switch (item.kind) {
    case 'OFFER': {
      const name = item.counterparty_name || t('messages:theOtherParty');
      const amount = item.amount_kes != null ? formatKes(item.amount_kes) : '';
      const who = item.from_viewer ? 'you' : item.from_fikisha ? 'fikisha' : 'they';
      const verb = item.entry_type === 'ACCEPT' ? 'Accepted' : item.entry_type === 'REJECT' ? 'Declined' : 'Offered';
      return {
        title: [kind, item.job_reference, item.counterparty_name].filter(Boolean).join(' · '),
        body: t(`messages:offer.${who}${verb}`, { name, amount }),
      };
    }
    case 'FIKISHA_UPDATE':
      return { title: `${kind} · ${item.job_reference}`, body: item.preview ?? '' };
    case 'INCIDENT': {
      const type = item.incident_type ? t(`incidents:report.type.${item.incident_type}`) : '';
      return {
        title: [kind, item.job_reference, type].filter(Boolean).join(' · '),
        body: item.preview || t(`incidents:detail.status.${item.status}`),
      };
    }
    case 'DISPUTE':
      return {
        title: `${kind} · ${item.job_reference}`,
        body: t(`incidents:detail.status.${item.status}`),
      };
  }
}
