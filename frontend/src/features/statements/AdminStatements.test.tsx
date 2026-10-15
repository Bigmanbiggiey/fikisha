import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Route, Routes } from 'react-router-dom';

import { ApiError } from '@/services/problem';
import { renderWithProviders } from '@/test/renderWithProviders';

import { AdminStatementDetailPage } from './AdminStatementDetailPage';
import { AdminStatementsPage } from './AdminStatementsPage';
import type { AdminStatementsPage as Page, StatementDetail, StatementSummary } from './types';

const meMock = vi.fn();
const api = {
  adminList: vi.fn(),
  adminGet: vi.fn(),
  run: vi.fn(),
  recordPayment: vi.fn(),
  reversePayment: vi.fn(),
};

vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: (...a: unknown[]) => meMock(...a), logout: vi.fn() },
}));
vi.mock('./statementsApi', () => ({
  statementsQueryKey: ['statements'],
  cursorFrom: (link: string | null) => link,
  statementsApi: {
    adminList: (...a: unknown[]) => api.adminList(...a),
    adminGet: (...a: unknown[]) => api.adminGet(...a),
    run: (...a: unknown[]) => api.run(...a),
    recordPayment: (...a: unknown[]) => api.recordPayment(...a),
    reversePayment: (...a: unknown[]) => api.reversePayment(...a),
  },
}));

function asRole(role: 'PLATFORM_ADMIN' | 'OPERATIONS_OFFICER'): void {
  meMock.mockResolvedValue({
    id: 'a1',
    phone: '+254700000009',
    display_name: 'Staff',
    locale: 'en',
    status: 'ACTIVE',
    roles: [role],
    is_admin: true,
  });
}

const summary: StatementSummary = {
  id: 's1',
  reference: 'ST-7B8BBA',
  payee: { kind: 'GROUP', id: 'g1', name: 'Pool Check Yard' },
  period_start: '2026-10-05',
  period_end: '2026-10-11',
  gross_commission_kes: 25_000,
  adjustments_kes: 0,
  net_due_kes: 25_000,
  settled_kes: 10_000,
  outstanding_kes: 15_000,
  state: 'PART_PAID',
  overdue: false,
  generated_at: '2026-10-12T03:00:00Z',
};

const listPage: Page = {
  data: [summary],
  page: { next_cursor: null, prev_cursor: null },
  totals: { statements: 1, invoiced_kes: 25_000, settled_kes: 10_000, outstanding_kes: 15_000 },
};

const detail: StatementDetail = {
  ...summary,
  lines: [
    {
      id: 'l1',
      kind: 'COMMISSION',
      job_id: 'j1',
      job_reference: 'F97DEA',
      agreed_price_kes: 250_000,
      amount_kes: 25_000,
    },
  ],
  settlements: [
    {
      id: 'p1',
      kind: 'PAYMENT',
      amount_kes: 10_000,
      method: 'MPESA_PAYBILL',
      payment_ref: 'SJK8QW1TZ',
      paid_on: '2026-10-14',
      note: '',
      reverses: null,
      reversed: false,
      recorded_at: '2026-10-14T08:00:00Z',
    },
  ],
  payment: { paybill_number: null, account_reference: 'ST-7B8BBA' },
};

beforeEach(() => {
  meMock.mockReset();
  for (const fn of Object.values(api)) fn.mockReset();
});

describe('AdminStatementsPage', () => {
  it('lists statements with invoiced vs paid totals', async () => {
    asRole('PLATFORM_ADMIN');
    api.adminList.mockResolvedValue(listPage);
    renderWithProviders(<AdminStatementsPage />);

    expect(await screen.findByRole('link', { name: 'ST-7B8BBA' })).toHaveAttribute(
      'href',
      '/ops/statements/s1',
    );
    expect(screen.getByText('Pool Check Yard')).toBeInTheDocument();
    expect(screen.getByText('Invoiced')).toBeInTheDocument();
    expect(screen.getAllByText('KSh 150').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Part paid').length).toBeGreaterThan(0);
  });

  it('lets a Platform Admin run a finished week', async () => {
    asRole('PLATFORM_ADMIN');
    api.adminList.mockResolvedValue(listPage);
    api.run.mockResolvedValue({
      period_start: '2026-10-05',
      period_end: '2026-10-11',
      statements_created: 2,
      statement_ids: ['a', 'b'],
      payees_skipped_existing: 1,
    });
    const user = userEvent.setup();
    renderWithProviders(<AdminStatementsPage />);

    await user.click(await screen.findByRole('button', { name: 'Run a week' }));
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: 'Run statements' }));

    await waitFor(() => expect(api.run).toHaveBeenCalledTimes(1));
    expect(api.run.mock.calls[0]![0]).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(await screen.findByText(/2 statements created/)).toBeInTheDocument();
  });

  it('gives an Operations Officer no run button', async () => {
    asRole('OPERATIONS_OFFICER');
    api.adminList.mockResolvedValue(listPage);
    renderWithProviders(<AdminStatementsPage />);
    await screen.findByRole('link', { name: 'ST-7B8BBA' });
    expect(screen.queryByRole('button', { name: 'Run a week' })).not.toBeInTheDocument();
  });
});

describe('AdminStatementDetailPage', () => {
  function renderAt(): void {
    renderWithProviders(
      <Routes>
        <Route path="/ops/statements/:statementId" element={<AdminStatementDetailPage />} />
      </Routes>,
      { route: '/ops/statements/s1' },
    );
  }

  it('records a payment after a confirm step that restates it', async () => {
    asRole('PLATFORM_ADMIN');
    api.adminGet.mockResolvedValue(detail);
    api.recordPayment.mockResolvedValue({
      ...detail,
      settled_kes: 25_000,
      outstanding_kes: 0,
      state: 'PAID',
    });
    const user = userEvent.setup();
    renderAt();

    await user.click(await screen.findByRole('button', { name: 'Record a payment' }));
    const dialog = await screen.findByRole('dialog');
    const amount = within(dialog).getByLabelText('Amount (KSh)');
    await user.type(amount, '200');
    // more than the KSh 150 still owed: can't continue
    expect(within(dialog).getByRole('button', { name: 'Continue' })).toBeDisabled();
    await user.clear(amount);
    await user.type(amount, '150');
    await user.type(within(dialog).getByLabelText('M-Pesa or bank reference'), 'sjk9ab2cd');
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }));

    expect(
      within(dialog).getByText('Record KSh 150 paid by Pool Check Yard against ST-7B8BBA'),
    ).toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: 'Record payment' }));

    await waitFor(() =>
      expect(api.recordPayment).toHaveBeenCalledWith(
        's1',
        expect.objectContaining({
          amount_kes: 15_000,
          payment_ref: 'SJK9AB2CD',
          method: 'MPESA_PAYBILL',
        }),
      ),
    );
    expect(await screen.findByText('Recorded KSh 150 (SJK9AB2CD).')).toBeInTheDocument();
  });

  it('shows the server refusal inside the dialog', async () => {
    asRole('PLATFORM_ADMIN');
    api.adminGet.mockResolvedValue(detail);
    api.recordPayment.mockRejectedValue(
      new ApiError(
        {
          type: 'about:blank',
          title: 'Conflict',
          status: 409,
          code: 'duplicate_payment_ref',
          detail: 'dup',
        },
        409,
        'dup',
      ),
    );
    const user = userEvent.setup();
    renderAt();

    await user.click(await screen.findByRole('button', { name: 'Record a payment' }));
    const dialog = await screen.findByRole('dialog');
    await user.type(within(dialog).getByLabelText('Amount (KSh)'), '100');
    await user.type(within(dialog).getByLabelText('M-Pesa or bank reference'), 'SJK8QW1TZ');
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }));
    await user.click(within(dialog).getByRole('button', { name: 'Record payment' }));

    expect(await within(dialog).findByText(/already recorded/)).toBeInTheDocument();
  });

  it('reverses a payment with a reason', async () => {
    asRole('PLATFORM_ADMIN');
    api.adminGet.mockResolvedValue(detail);
    api.reversePayment.mockResolvedValue({
      ...detail,
      settled_kes: 0,
      outstanding_kes: 25_000,
      state: 'UNPAID',
    });
    const user = userEvent.setup();
    renderAt();

    await user.click(await screen.findByRole('button', { name: 'Reverse' }));
    const dialog = await screen.findByRole('dialog');
    await user.type(within(dialog).getByRole('textbox'), 'Recorded against the wrong week');
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }));
    await user.click(within(dialog).getByRole('button', { name: 'Reverse payment' }));

    await waitFor(() =>
      expect(api.reversePayment).toHaveBeenCalledWith(
        's1',
        'p1',
        'Recorded against the wrong week',
      ),
    );
    expect(await screen.findByText('Payment SJK8QW1TZ reversed.')).toBeInTheDocument();
  });

  it('is read-only for an Operations Officer', async () => {
    asRole('OPERATIONS_OFFICER');
    api.adminGet.mockResolvedValue(detail);
    renderAt();
    expect(await screen.findByRole('heading', { level: 1, name: 'ST-7B8BBA' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Record a payment' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Reverse' })).not.toBeInTheDocument();
  });
});
