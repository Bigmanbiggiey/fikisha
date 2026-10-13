import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Route, Routes } from 'react-router-dom';

import { renderWithProviders } from '@/test/renderWithProviders';

import { MessagesPage } from './MessagesPage';
import type { MessageItem } from './types';

const list = vi.fn();
const markRead = vi.fn();

vi.mock('./messagesApi', () => ({
  messagesQueryKey: ['messages'],
  messagesApi: {
    list: (...a: unknown[]) => list(...a),
    markRead: (...a: unknown[]) => markRead(...a),
  },
}));
vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: () => Promise.reject(new Error('anon')), logout: vi.fn() },
}));

const now = new Date().toISOString();
const items: MessageItem[] = [
  {
    conversation_key: 'offer:t1',
    kind: 'OFFER',
    job_id: 'j1',
    job_reference: '1C5238',
    at: now,
    unread: true,
    link: '/jobs/j1/negotiation',
    counterparty_name: 'A. Otieno',
    entry_type: 'COUNTER',
    amount_kes: 240_000,
    from_viewer: false,
  },
  {
    conversation_key: 'notes:j1',
    kind: 'FIKISHA_UPDATE',
    job_id: 'j1',
    job_reference: '1C5238',
    at: now,
    unread: false,
    link: '/jobs/j1',
    preview: 'Driver is 20 minutes late',
    count: 1,
  },
  {
    conversation_key: 'incident:i1',
    kind: 'INCIDENT',
    job_id: 'j2',
    job_reference: '30EDE6',
    at: now,
    unread: false,
    link: '/incidents/i1',
    status: 'UNDER_REVIEW',
    incident_type: 'DAMAGE',
    preview: '',
  },
];

function renderPage(): void {
  renderWithProviders(
    <Routes>
      <Route path="/messages" element={<MessagesPage />} />
      <Route path="/jobs/:jobId/negotiation" element={<div>Negotiation screen</div>} />
    </Routes>,
    { route: '/messages' },
  );
}

describe('MessagesPage (Design Phase 7 10g)', () => {
  beforeEach(() => {
    list.mockReset();
    markRead.mockReset();
    list.mockResolvedValue({ data: items, page: { next_cursor: null, prev_cursor: null }, unread_count: 1 });
    markRead.mockResolvedValue(null);
  });

  it('lists every conversation, worded from the reader’s side, with the unread one marked', async () => {
    renderPage();
    const offer = await screen.findByRole('button', { name: /Offer · 1C5238 · A. Otieno/ });
    expect(offer).toHaveTextContent('A. Otieno offered KSh 2,400');
    expect(within(offer).getByText('Unread')).toHaveClass('sr-only');

    const update = screen.getByRole('button', { name: /Update from Fikisha · 1C5238/ });
    expect(update).toHaveTextContent('Driver is 20 minutes late');
    expect(within(update).queryByText('Unread')).not.toBeInTheDocument();

    // An issue with no statement text falls back to its status.
    expect(screen.getByRole('button', { name: /Issue · 30EDE6 · Damage/ })).toHaveTextContent('Under review');
  });

  it('credits an entry staff posted to Fikisha, not to the counterparty', async () => {
    list.mockResolvedValue({
      data: [{ ...items[0], from_fikisha: true }],
      page: { next_cursor: null, prev_cursor: null },
      unread_count: 1,
    });
    renderPage();
    const offer = await screen.findByRole('button', { name: /Offer · 1C5238/ });
    expect(offer).toHaveTextContent('Fikisha offered KSh 2,400');
    expect(offer).not.toHaveTextContent('A. Otieno offered');
  });

  it('filters by kind', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByRole('button', { name: /Offer · 1C5238/ });

    await user.click(screen.getByRole('button', { name: 'Issues' }));
    expect(screen.getByRole('button', { name: 'Issues' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.queryByRole('button', { name: /Offer · 1C5238/ })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Issue · 30EDE6/ })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Fikisha updates' }));
    expect(screen.getByRole('button', { name: /Update from Fikisha/ })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Issue · 30EDE6/ })).not.toBeInTheDocument();
  });

  it('marks an unread conversation read and opens its screen', async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: /Offer · 1C5238/ }));
    expect(markRead).toHaveBeenCalledWith('offer:t1');
    expect(await screen.findByText('Negotiation screen')).toBeInTheDocument();
  });

  it('says so when there are no messages yet', async () => {
    list.mockResolvedValue({ data: [], page: { next_cursor: null, prev_cursor: null }, unread_count: 0 });
    renderPage();
    expect(await screen.findByText('No messages yet')).toBeInTheDocument();
  });
});
