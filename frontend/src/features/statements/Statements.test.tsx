import { screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Route, Routes } from 'react-router-dom';

import { renderWithProviders } from '@/test/renderWithProviders';

import { JobEarningsCard } from './JobEarningsCard';
import { NewStatementCard } from './NewStatementCard';
import { StatementDetailPage } from './StatementDetailPage';
import { StatementsPage } from './StatementsPage';
import type {
  JobEarnings,
  StatementDetail,
  StatementSummary,
  StatementsPage as Page,
} from './types';

const list = vi.fn();
const get = vi.fn();
const markSeen = vi.fn();
const jobEarnings = vi.fn();

vi.mock('./statementsApi', () => ({
  statementsQueryKey: ['statements'],
  cursorFrom: (link: string | null) => link,
  statementsApi: {
    list: (...a: unknown[]) => list(...a),
    get: (...a: unknown[]) => get(...a),
    markSeen: (...a: unknown[]) => markSeen(...a),
    jobEarnings: (...a: unknown[]) => jobEarnings(...a),
  },
}));
vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: () => Promise.reject(new Error('anon')), logout: vi.fn() },
}));

function summary(overrides: Partial<StatementSummary> = {}): StatementSummary {
  return {
    id: 's1',
    reference: 'ST-7F3A2C',
    payee: { kind: 'OPERATOR', id: 'op1', name: 'D. Kamau' },
    period_start: '2026-10-05',
    period_end: '2026-10-11',
    gross_commission_kes: 50_000,
    adjustments_kes: 0,
    net_due_kes: 50_000,
    settled_kes: 0,
    outstanding_kes: 50_000,
    state: 'UNPAID',
    overdue: false,
    generated_at: '2026-10-12T03:00:00Z',
    seen: false,
    ...overrides,
  };
}

function page(
  rows: StatementSummary[],
  unseen = rows.filter((r) => r.seen === false).length,
): Page {
  return { data: rows, page: { next_cursor: null, prev_cursor: null }, unseen_count: unseen };
}

function detail(overrides: Partial<StatementDetail> = {}): StatementDetail {
  return {
    ...summary(),
    lines: [
      {
        id: 'l1',
        kind: 'COMMISSION',
        job_id: 'j1',
        job_reference: '1C5238',
        agreed_price_kes: 250_000,
        amount_kes: 25_000,
      },
      {
        id: 'l2',
        kind: 'COMMISSION',
        job_id: 'j2',
        job_reference: '30EDE6',
        agreed_price_kes: 250_000,
        amount_kes: 25_000,
      },
    ],
    settlements: [],
    payment: { paybill_number: null, account_reference: 'ST-7F3A2C' },
    ...overrides,
  };
}

beforeEach(() => {
  list.mockReset();
  get.mockReset();
  markSeen.mockReset().mockResolvedValue(null);
  jobEarnings.mockReset();
});

describe('StatementsPage', () => {
  it('lists statements with state, amount and an unseen marker', async () => {
    list.mockResolvedValue(
      page([
        summary(),
        summary({
          id: 's0',
          reference: 'ST-111111',
          state: 'PAID',
          outstanding_kes: 0,
          seen: true,
        }),
      ]),
    );
    renderWithProviders(<StatementsPage />);

    expect(await screen.findByText('ST-7F3A2C')).toBeInTheDocument();
    expect(screen.getByText('Unpaid')).toBeInTheDocument();
    expect(screen.getByText('Paid')).toBeInTheDocument();
    expect(screen.getAllByText('KSh 500')).toHaveLength(2);
    // only the unopened one carries the "New" marker
    expect(screen.getAllByText(/New/)).toHaveLength(1);
    expect(screen.getByRole('link', { name: /ST-7F3A2C/ })).toHaveAttribute(
      'href',
      '/statements/s1',
    );
  });

  it('shows overdue ahead of unpaid', async () => {
    list.mockResolvedValue(page([summary({ overdue: true })]));
    renderWithProviders(<StatementsPage />);
    expect(await screen.findByText('Overdue')).toBeInTheDocument();
  });

  it('explains when there are no statements yet', async () => {
    list.mockResolvedValue(page([]));
    renderWithProviders(<StatementsPage />);
    expect(await screen.findByText('No statements yet')).toBeInTheDocument();
  });
});

describe('StatementDetailPage', () => {
  function renderAt(id: string): void {
    renderWithProviders(
      <Routes>
        <Route path="/statements/:statementId" element={<StatementDetailPage />} />
      </Routes>,
      { route: `/statements/${id}` },
    );
  }

  it('shows the jobs, totals and "not a tax invoice", and marks it seen', async () => {
    get.mockResolvedValue(detail());
    renderAt('s1');

    expect(await screen.findByRole('heading', { level: 1, name: 'ST-7F3A2C' })).toBeInTheDocument();
    expect(screen.getByText(/not a tax invoice/)).toBeInTheDocument();
    expect(screen.getByText('2 jobs')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '1C5238' })).toHaveAttribute('href', '/jobs/j1');
    // the paybill isn't set yet: details to follow, with the account number
    expect(screen.getByText(/Payment details will follow.*ST-7F3A2C/)).toBeInTheDocument();
    await waitFor(() => expect(markSeen).toHaveBeenCalledWith('s1'));
  });

  it('shows the paybill once set, and payments with a reversal', async () => {
    get.mockResolvedValue(
      detail({
        payment: { paybill_number: '400200', account_reference: 'ST-7F3A2C' },
        settled_kes: 20_000,
        outstanding_kes: 30_000,
        state: 'PART_PAID',
        settlements: [
          {
            id: 'p1',
            kind: 'PAYMENT',
            amount_kes: 50_000,
            method: 'MPESA_PAYBILL',
            payment_ref: 'SJK1',
            paid_on: '2026-10-13',
            note: '',
            reverses: null,
            reversed: true,
            recorded_at: '2026-10-13T08:00:00Z',
          },
          {
            id: 'p2',
            kind: 'REVERSAL',
            amount_kes: -50_000,
            method: 'MPESA_PAYBILL',
            payment_ref: 'SJK1',
            paid_on: '2026-10-13',
            note: 'Recorded against the wrong week',
            reverses: 'p1',
            reversed: false,
            recorded_at: '2026-10-13T09:00:00Z',
          },
          {
            id: 'p3',
            kind: 'PAYMENT',
            amount_kes: 20_000,
            method: 'MPESA_PAYBILL',
            payment_ref: 'SJK2',
            paid_on: '2026-10-14',
            note: '',
            reverses: null,
            reversed: false,
            recorded_at: '2026-10-14T08:00:00Z',
          },
        ],
      }),
    );
    renderAt('s1');

    expect(await screen.findByText('400200')).toBeInTheDocument();
    expect(screen.getByText('Part paid')).toBeInTheDocument();
    expect(screen.getByText('Reversed · SJK1')).toBeInTheDocument();
    expect(screen.getByText('Recorded against the wrong week')).toBeInTheDocument();
    expect(screen.getAllByText('KSh 300').length).toBeGreaterThan(0);
  });

  it('hides "how to pay" when a credit leaves nothing to pay', async () => {
    get.mockResolvedValue(
      detail({
        lines: [
          {
            id: 'l3',
            kind: 'ADJUSTMENT',
            job_id: 'j1',
            job_reference: '1C5238',
            agreed_price_kes: null,
            amount_kes: -5_000,
          },
        ],
        gross_commission_kes: 0,
        adjustments_kes: -5_000,
        net_due_kes: -5_000,
        outstanding_kes: 0,
        state: 'PAID',
      }),
    );
    renderAt('s1');

    expect(await screen.findByText(/credits are larger than this week/)).toBeInTheDocument();
    expect(screen.queryByText('How to pay')).not.toBeInTheDocument();
    expect(screen.getByText(/No new jobs this week/)).toBeInTheDocument();
  });
});

describe('JobEarningsCard', () => {
  const earnings: JobEarnings = {
    job_id: 'j1',
    payee_kind: 'OPERATOR',
    payee_id: 'op1',
    agreed_price_kes: 250_000,
    commission_kes: 25_000,
    adjustments_kes: 0,
    effective_commission_kes: 25_000,
    net_to_operator_kes: 225_000,
    statement: { id: 's1', reference: 'ST-7F3A2C' },
  };

  it('shows agreed − commission = net and links the statement', async () => {
    jobEarnings.mockResolvedValue(earnings);
    renderWithProviders(<JobEarningsCard jobId="j1" />);
    expect(await screen.findByText('KSh 2,250')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'ST-7F3A2C' })).toHaveAttribute(
      'href',
      '/statements/s1',
    );
  });

  it('says when the job is not billed yet', async () => {
    jobEarnings.mockResolvedValue({ ...earnings, statement: null });
    renderWithProviders(<JobEarningsCard jobId="j1" />);
    expect(await screen.findByText(/once the dispute window closes/)).toBeInTheDocument();
  });

  it('stays hidden when the server refuses (not the payee)', async () => {
    jobEarnings.mockRejectedValue(new Error('404'));
    const { container } = renderWithProviders(<JobEarningsCard jobId="j1" />);
    await waitFor(() => expect(jobEarnings).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });
});

describe('NewStatementCard', () => {
  it('points to the newest unopened statement', async () => {
    list.mockResolvedValue(page([summary()]));
    renderWithProviders(<NewStatementCard />);
    expect(await screen.findByText('New statement')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'View statement' })).toHaveAttribute(
      'href',
      '/statements/s1',
    );
  });

  it('shows nothing when every statement has been opened', async () => {
    list.mockResolvedValue(page([summary({ seen: true })]));
    const { container } = renderWithProviders(<NewStatementCard />);
    await waitFor(() => expect(list).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });
});
