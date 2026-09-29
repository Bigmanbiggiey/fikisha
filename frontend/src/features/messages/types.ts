/** One inbox conversation (`GET /messages`, ADR-2D-37). The backend sends
 * structured fields, not sentences, so every line is written here in the
 * reader's language. */
export type MessageKind = 'OFFER' | 'FIKISHA_UPDATE' | 'INCIDENT' | 'DISPUTE';

export interface MessageItem {
  conversation_key: string;
  kind: MessageKind;
  job_id: string;
  job_reference: string;
  /** ISO time of the conversation's latest activity */
  at: string;
  unread: boolean;
  /** the screen this conversation lives on */
  link: string;
  preview?: string | null;
  // OFFER
  counterparty_name?: string | null;
  thread_status?: string;
  entry_type?: 'PROPOSE' | 'COUNTER' | 'ACCEPT' | 'REJECT';
  amount_kes?: number | null;
  from_viewer?: boolean;
  /** posted by Fikisha staff, not by either party */
  from_fikisha?: boolean;
  // FIKISHA_UPDATE
  count?: number;
  // INCIDENT / DISPUTE
  status?: string;
  incident_type?: string | null;
}

export interface MessagesPage {
  data: MessageItem[];
  page: { next_cursor: string | null; prev_cursor: string | null };
  /** unread conversations across the whole inbox, not just this page */
  unread_count: number;
}
