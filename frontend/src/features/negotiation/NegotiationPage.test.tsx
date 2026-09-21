import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Route, Routes } from 'react-router-dom';

import { ApiError } from '@/services/problem';
import { renderWithProviders } from '@/test/renderWithProviders';

import { NegotiationPage } from './NegotiationPage';
import type { NegotiationThread } from './types';

const get = vi.fn();
const listThreads = vi.fn();
const counter = vi.fn();
const accept = vi.fn();
const decline = vi.fn();

vi.mock('@/features/jobs/jobsApi', () => ({
  jobsApi: { get: (...a: unknown[]) => get(...a) },
}));
vi.mock('./negotiationApi', () => ({
  negotiationApi: {
    listThreads: (...a: unknown[]) => listThreads(...a),
    counter: (...a: unknown[]) => counter(...a),
    accept: (...a: unknown[]) => accept(...a),
    decline: (...a: unknown[]) => decline(...a),
  },
}));
const meMock = vi.fn();
const listBusinesses = vi.fn();
const getMyOperator = vi.fn();
const listGroups = vi.fn();

vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: (...a: unknown[]) => meMock(...a), logout: vi.fn() },
}));
vi.mock('@/features/org/orgApi', () => ({
  orgApi: {
    listBusinesses: (...a: unknown[]) => listBusinesses(...a),
    getMyOperator: (...a: unknown[]) => getMyOperator(...a),
    listGroups: (...a: unknown[]) => listGroups(...a),
  },
}));

function renderAtJob(jobId: string): ReturnType<typeof renderWithProviders> {
  return renderWithProviders(
    <Routes>
      <Route path="/jobs/:jobId/negotiation" element={<NegotiationPage />} />
    </Routes>,
    { route: `/jobs/${jobId}/negotiation` },
  );
}

function baseJob(): Record<string, unknown> {
  return {
    id: '01a0a4123456',
    business_id: 'biz1',
    status: 'NEGOTIATING',
    pickup_location: { address_text: 'Depot, Kitengela' },
    destination_location: { address_text: 'Shop 4, Kitengela' },
    cargo: { description: '20 cartons' },
  };
}

function baseThread(overrides: Partial<NegotiationThread> = {}): NegotiationThread {
  return {
    thread_id: 'th1',
    job_id: '01a0a4123456',
    job_status: 'NEGOTIATING',
    status: 'ACTIVE',
    operator_party: 'OPERATOR',
    operator_id: 'op1',
    group_id: null,
    operator_display_name: 'Athi Movers',
    standing_offer: { entry_id: 'e2', actor_role: 'OPERATOR', amount_kes: 780_000 },
    counterparty_offer: { entry_id: 'e2', amount_kes: 780_000 },
    mutual_acceptance: { reached: false, amount_kes: null, entry_ids: [] },
    entries: [
      {
        id: 'e1',
        actor_role: 'BUSINESS',
        type: 'PROPOSE',
        amount_kes: 750_000,
        note: '',
        in_response_to_id: null,
        created_at: '2026-09-15T13:10:00Z',
        expires_at: null,
        effective_status: 'SUPERSEDED',
      },
      {
        id: 'e2',
        actor_role: 'OPERATOR',
        type: 'COUNTER',
        amount_kes: 780_000,
        note: 'Fuel is high today.',
        in_response_to_id: 'e1',
        created_at: '2026-09-15T13:14:00Z',
        expires_at: '2026-09-16T13:14:00Z',
        effective_status: 'ACTIVE',
      },
    ],
    ...overrides,
  };
}

describe('NegotiationPage', () => {
  beforeEach(() => {
    get.mockReset();
    listThreads.mockReset();
    counter.mockReset();
    accept.mockReset();
    decline.mockReset();
    meMock.mockReset();
    listBusinesses.mockReset();
    getMyOperator.mockReset();
    listGroups.mockReset();
    get.mockResolvedValue(baseJob());
    meMock.mockRejectedValue(new Error('anon'));
  });

  it('shows the offer history and lets the business accept the operator\'s offer', async () => {
    listThreads.mockResolvedValue({ data: [baseThread()] });
    const user = userEvent.setup();
    renderAtJob('01a0a4123456');

    expect(await screen.findByText('Athi Movers')).toBeInTheDocument();
    expect(screen.getByText('Fuel is high today.')).toBeInTheDocument();

    const acceptButton = screen.getByRole('button', { name: 'Accept KSh 7,800' });
    accept.mockResolvedValue({ ...baseThread(), status: 'CLOSED', confirmed: true });
    await user.click(acceptButton);

    expect(accept).toHaveBeenCalledWith('th1', { amount_kes: 780_000 }, expect.any(String));
  });

  it('refetches the thread when accept fails because the counterparty offer is gone', async () => {
    // Regression: onError previously only refreshed for 'invalid_offer',
    // leaving a stale Accept button visible after 'nothing_to_accept'
    // (raised when the counterparty's offer disappeared between page load
    // and the click) — a retry would just repeat the same error forever.
    listThreads.mockResolvedValue({ data: [baseThread()] });
    const user = userEvent.setup();
    renderAtJob('01a0a4123456');

    const acceptButton = await screen.findByRole('button', { name: 'Accept KSh 7,800' });
    accept.mockRejectedValueOnce(
      new ApiError(
        {
          type: 'about:blank',
          title: 'Nothing to accept',
          status: 409,
          code: 'nothing_to_accept',
          detail: 'The counterparty offer is no longer available.',
        },
        409,
        'The counterparty offer is no longer available.',
      ),
    );
    const callsBeforeRetry = listThreads.mock.calls.length;
    await user.click(acceptButton);

    await waitFor(() => expect(listThreads.mock.calls.length).toBeGreaterThan(callsBeforeRetry));
  });

  it('sends a counter-offer through the composer', async () => {
    listThreads.mockResolvedValue({ data: [baseThread()] });
    const user = userEvent.setup();
    renderAtJob('01a0a4123456');

    await screen.findByText('Athi Movers');
    await user.click(screen.getByRole('button', { name: 'Send counter' }));

    const amountInput = screen.getByLabelText('Your counter-offer (KSh)');
    await user.type(amountInput, '7600');

    counter.mockResolvedValue({ ...baseThread() });
    await user.click(screen.getByRole('button', { name: 'Send' }));

    expect(counter).toHaveBeenCalledWith(
      'th1',
      { amount_kes: 760_000, note: undefined },
      expect.any(String),
    );
  });

  it('declines the thread', async () => {
    listThreads.mockResolvedValue({ data: [baseThread()] });
    const user = userEvent.setup();
    renderAtJob('01a0a4123456');

    await screen.findByText('Athi Movers');
    decline.mockResolvedValue({ ...baseThread(), status: 'CLOSED' });
    await user.click(screen.getByRole('button', { name: 'Decline' }));

    expect(decline).toHaveBeenCalledWith('th1', {}, expect.any(String));
  });

  it('shows a "waiting for operator" state once the business has already accepted', async () => {
    listThreads.mockResolvedValue({
      data: [
        baseThread({
          entries: [
            ...baseThread().entries,
            {
              id: 'e3',
              actor_role: 'BUSINESS',
              type: 'ACCEPT',
              amount_kes: 780_000,
              note: '',
              in_response_to_id: 'e2',
              created_at: '2026-09-15T13:20:00Z',
              expires_at: null,
              effective_status: 'ACTIVE',
            },
          ],
        }),
      ],
    });
    renderAtJob('01a0a4123456');

    expect(await screen.findByText("Waiting for the operator's next move.")).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Accept/ })).not.toBeInTheDocument();
  });

  it('shows the agreed banner and an Open Job action once mutual acceptance is reached', async () => {
    listThreads.mockResolvedValue({
      data: [
        baseThread({
          status: 'CLOSED',
          mutual_acceptance: { reached: true, amount_kes: 780_000, entry_ids: ['e2', 'e3'] },
        }),
      ],
    });
    renderAtJob('01a0a4123456');

    expect(await screen.findByText('Agreed: KSh 7,800')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Open Job' })).toBeInTheDocument();
  });

  it('shows a picker when more than one operator has responded', async () => {
    listThreads.mockResolvedValue({
      data: [
        baseThread({ thread_id: 'th1', operator_display_name: 'Athi Movers' }),
        baseThread({ thread_id: 'th2', operator_display_name: 'Kitengela Yard', operator_id: 'op2' }),
      ],
    });
    const user = userEvent.setup();
    renderAtJob('01a0a4123456');

    expect(await screen.findByText('Offers (2)')).toBeInTheDocument();
    expect(screen.getByText('Athi Movers')).toBeInTheDocument();
    expect(screen.getByText('Kitengela Yard')).toBeInTheDocument();

    await user.click(screen.getByText('Kitengela Yard'));
    await waitFor(() => expect(screen.getByRole('button', { name: '← Back to offers' })).toBeInTheDocument());
  });

  it('shows an empty state when no operator has responded yet', async () => {
    listThreads.mockResolvedValue({ data: [] });
    renderAtJob('01a0a4123456');

    expect(await screen.findByText('No offers yet')).toBeInTheDocument();
  });

  describe('as the operator viewer', () => {
    beforeEach(() => {
      // Increment 4: the signed-in user holds an Operator workspace and no
      // Business workspace that owns this job's business_id, so
      // useJobViewerRole resolves 'OPERATOR' — the same shared component now
      // renders the operator's side of the exact same thread.
      meMock.mockResolvedValue({
        id: 'u2',
        phone: '+254733200001',
        display_name: 'D. Kamau',
        locale: 'en',
        status: 'ACTIVE',
        roles: [],
        is_admin: false,
      });
      listBusinesses.mockResolvedValue({ data: [], page: { next_cursor: null, prev_cursor: null } });
      getMyOperator.mockResolvedValue({ id: 'op1', full_name: 'D. Kamau', display_name: '' });
      listGroups.mockResolvedValue({ data: [], page: { next_cursor: null, prev_cursor: null } });
    });

    it('lets the operator accept the business\'s standing offer, falling back to a generic counterparty label', async () => {
      listThreads.mockResolvedValue({
        data: [
          baseThread({
            // From the operator's own side: the standing/counterparty offer
            // is now the BUSINESS's figure, resolved server-side.
            standing_offer: { entry_id: 'e1', actor_role: 'BUSINESS', amount_kes: 750_000 },
            counterparty_offer: { entry_id: 'e1', amount_kes: 750_000 },
          }),
        ],
      });
      const user = userEvent.setup();
      renderAtJob('01a0a4123456');

      // No business_display_name exists on the payload (ADR-2D-31 gap) — the
      // business's entry must show the generic fallback, never the
      // operator's own name (operator_display_name would be wrong here).
      expect(await screen.findByText('Business')).toBeInTheDocument();
      expect(screen.queryByText('Athi Movers')).not.toBeInTheDocument();

      const acceptButton = screen.getByRole('button', { name: 'Accept KSh 7,500' });
      accept.mockResolvedValue({ ...baseThread(), confirmed: false });
      await user.click(acceptButton);

      expect(accept).toHaveBeenCalledWith('th1', { amount_kes: 750_000 }, expect.any(String));
    });

    it('shows a "waiting for the business" state once the operator has already accepted', async () => {
      listThreads.mockResolvedValue({
        data: [
          baseThread({
            entries: [
              ...baseThread().entries,
              {
                id: 'e3',
                actor_role: 'OPERATOR',
                type: 'ACCEPT',
                amount_kes: 750_000,
                note: '',
                in_response_to_id: 'e1',
                created_at: '2026-09-15T13:20:00Z',
                expires_at: null,
                effective_status: 'ACTIVE',
              },
            ],
          }),
        ],
      });
      renderAtJob('01a0a4123456');

      expect(await screen.findByText("Waiting for the business's next move.")).toBeInTheDocument();
    });
  });
});
