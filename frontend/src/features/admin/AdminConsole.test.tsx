import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Route, Routes } from 'react-router-dom';

import { ApiError } from '@/services/problem';
import { renderWithProviders } from '@/test/renderWithProviders';

import { CommissionPage } from './CommissionPage';
import { ConfigPage } from './ConfigPage';
import { DirectoryDetailPage } from './DirectoryDetailPage';
import { DirectoryPage } from './DirectoryPage';

const meMock = vi.fn();
const api = {
  directory: vi.fn(),
  detail: vi.fn(),
  revealContact: vi.fn(),
  intervene: vi.fn(),
  config: vi.fn(),
  previewConfig: vi.fn(),
  applyConfig: vi.fn(),
  commission: vi.fn(),
};

vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: (...a: unknown[]) => meMock(...a), logout: vi.fn() },
}));
vi.mock('./adminApi', () => ({
  adminApi: new Proxy(
    {},
    {
      get:
        (_t, key: string) =>
        (...a: unknown[]) =>
          api[key as keyof typeof api](...a),
    },
  ),
  cursorFrom: (link: string | null) => link,
}));

const page = <T,>(data: T[]) => ({ data, page: { next_cursor: null, prev_cursor: null } });
const stepUp = () =>
  new ApiError(
    { type: 'about:blank', title: 'Forbidden', status: 403, code: 'step_up_required', detail: '' },
    403,
    '',
  );

function detail(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: 'op-1',
    kind: 'OPERATOR',
    name: 'A. Otieno',
    state: 'ACTIVE',
    phone: '+2547•••••678',
    created_at: '2026-10-01T08:00:00Z',
    user_id: 'u-1',
    user_status: 'ACTIVE',
    in_flight_jobs: [{ id: 'job-1', reference: 'ABC123', status: 'ASSIGNED' }],
    interventions: [],
    user_interventions: [],
    ...overrides,
  };
}

beforeEach(() => {
  meMock.mockReset();
  for (const fn of Object.values(api)) fn.mockReset();
  meMock.mockResolvedValue({
    id: 'a1',
    phone: '+254700000009',
    display_name: 'Admin',
    locale: 'en',
    status: 'ACTIVE',
    roles: ['PLATFORM_ADMIN'],
    is_admin: true,
  });
});

describe('Users & organizations', () => {
  it('lists masked rows and switches directory', async () => {
    api.directory.mockResolvedValue(
      page([
        {
          id: 'b-1',
          kind: 'BUSINESS',
          name: 'Kitengela Traders',
          state: 'GOOD',
          phone: '+2547•••••001',
          member_count: 2,
          created_at: '',
        },
      ]),
    );
    renderWithProviders(<DirectoryPage />, { route: '/admin/directory' });

    expect(await screen.findByText('Kitengela Traders')).toBeInTheDocument();
    expect(screen.getByText(/\+2547•••••001/)).toBeInTheDocument();
    expect(within(screen.getByRole('list')).getByText('Good standing')).toBeInTheDocument();
    expect(api.directory).toHaveBeenCalledWith('businesses', { q: '', state: '' }, null);

    await userEvent.click(screen.getByRole('button', { name: 'Operators' }));
    await waitFor(() =>
      expect(api.directory).toHaveBeenLastCalledWith('operators', { q: '', state: '' }, null),
    );
  });
});

describe('directory detail', () => {
  function renderDetail(): void {
    renderWithProviders(
      <Routes>
        <Route path="/admin/directory/:kind/:id" element={<DirectoryDetailPage />} />
      </Routes>,
      { route: '/admin/directory/operators/op-1' },
    );
  }

  it('shows running jobs and reveals the full number on request', async () => {
    api.detail.mockResolvedValue(detail());
    api.revealContact.mockResolvedValue({ name: 'A. Otieno', phone: '+254712345678' });
    renderDetail();

    expect(await screen.findByRole('heading', { name: 'A. Otieno' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'ABC123' })).toHaveAttribute('href', '/jobs/job-1');
    expect(screen.queryByText('+254712345678')).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Show full number' }));
    expect(await screen.findByRole('link', { name: '0712345678' })).toHaveAttribute(
      'href',
      'tel:+254712345678',
    );
  });

  it('offers actions that fit the state', async () => {
    api.detail.mockResolvedValue(detail({ state: 'SUSPENDED' }));
    renderDetail();
    await screen.findByRole('heading', { name: 'A. Otieno' });
    expect(screen.getByRole('button', { name: 'Reinstate account' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Offboard account' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Suspend account' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Suspend sign-in' })).toBeInTheDocument();
  });

  it('asks for a reason, restates the action, and says plainly when MFA is missing', async () => {
    api.detail.mockResolvedValue(detail());
    api.intervene.mockRejectedValue(stepUp());
    renderDetail();
    await userEvent.click(await screen.findByRole('button', { name: 'Suspend account' }));

    const dialog = await screen.findByRole('dialog');
    const next = within(dialog).getByRole('button', { name: 'Continue' });
    expect(next).toBeDisabled();
    await userEvent.type(within(dialog).getByLabelText('Reason'), 'short');
    expect(next).toBeDisabled();
    await userEvent.type(within(dialog).getByLabelText('Reason'), ' but now long enough');
    await userEvent.type(within(dialog).getByLabelText('Expected length in days (optional)'), '14');
    await userEvent.click(next);

    expect(within(dialog).getByText('Suspend A. Otieno.')).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole('button', { name: 'Suspend' }));
    expect(api.intervene).toHaveBeenCalledWith({
      account_type: 'OPERATOR',
      account_id: 'op-1',
      action: 'SUSPEND',
      reason: 'short but now long enough',
      duration_days: 14,
    });
    expect(
      await within(dialog).findByText(/needs a fresh authenticator code. Nothing was changed/),
    ).toBeInTheDocument();
  });
});

describe('Configuration', () => {
  const view = {
    version: 3,
    config: {
      commission: { rate: 0.1, min_fee_kes: 4000, cap_kes: 500000 },
      timeouts: { offer_expiry_hours: 4 },
      value_bands: [],
      role_permissions: {},
    },
    editable_paths: ['commission.rate', 'commission.min_fee_kes', 'timeouts.offer_expiry_hours'],
    versions: [
      {
        version: 3,
        changed_by_user_id: null,
        changed_by_name: null,
        rationale: 'Bootstrap',
        created_at: '2026-10-01T08:00:00Z',
      },
    ],
  };

  it('the live-criteria switch is a yes/no box (trust plan A5)', async () => {
    api.config.mockResolvedValue({
      ...view,
      config: { ...view.config, trust_tiers: { live_criteria: false } },
      editable_paths: [...view.editable_paths, 'trust_tiers.live_criteria'],
    });
    api.previewConfig.mockResolvedValue({ version: 3, changes: [], commission_samples: [] });
    renderWithProviders(<ConfigPage />);

    const box = await screen.findByLabelText('Ratings and fault findings count toward tiers');
    expect(box).not.toBeChecked();
    await userEvent.click(box);
    await userEvent.click(screen.getByRole('button', { name: 'Preview changes' }));
    expect(api.previewConfig).toHaveBeenCalledWith({ 'trust_tiers.live_criteria': true });
  });

  it('previews a change in people units and sends config units', async () => {
    api.config.mockResolvedValue(view);
    api.previewConfig.mockResolvedValue({
      version: 3,
      changes: [{ path: 'commission.rate', before: 0.1, after: 0.08 }],
      commission_samples: [{ agreed_price_kes: 300000, before_kes: 30000, after_kes: 24000 }],
    });
    api.applyConfig.mockRejectedValue(stepUp());
    renderWithProviders(<ConfigPage />);

    const rate = await screen.findByLabelText('Commission rate (%)');
    expect(rate).toHaveValue('10');
    expect(screen.getByLabelText('Minimum commission (KSh)')).toHaveValue('40');
    expect(screen.getByRole('button', { name: 'Preview changes' })).toBeDisabled();

    await userEvent.clear(rate);
    await userEvent.type(rate, '8');
    await userEvent.click(screen.getByRole('button', { name: 'Preview changes' }));
    expect(api.previewConfig).toHaveBeenCalledWith({ 'commission.rate': 0.08 });
    expect(await screen.findByText('KSh 240')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Apply…' }));
    const dialog = await screen.findByRole('dialog');
    await userEvent.type(within(dialog).getByLabelText('Reason'), 'Pilot test of a lower rate');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Continue' }));
    await userEvent.click(within(dialog).getByRole('button', { name: 'Apply' }));
    expect(api.applyConfig).toHaveBeenCalledWith(
      { 'commission.rate': 0.08 },
      'Pilot test of a lower rate',
    );
    expect(await within(dialog).findByText(/needs a fresh authenticator code/)).toBeInTheDocument();
  });

  it('flags a value that is not a number', async () => {
    api.config.mockResolvedValue(view);
    renderWithProviders(<ConfigPage />);
    const hours = await screen.findByLabelText('Offer expires after (hours)');
    await userEvent.clear(hours);
    await userEvent.type(hours, 'soon');
    expect(screen.getByText('Check the highlighted values.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Preview changes' })).toBeDisabled();
  });
});

describe('Commission', () => {
  it('shows the ledger, totals and a link to the weekly statements', async () => {
    api.commission.mockResolvedValue({
      ...page([
        {
          id: 'c-1',
          job_id: 'job-1',
          job_reference: 'ABC123',
          business_name: 'Kitengela Traders',
          payee: { kind: 'OPERATOR', id: 'op-1', name: 'A. Otieno' },
          agreed_price_kes: 300000,
          rate: '0.1000',
          min_fee_kes: 4000,
          cap_kes: 500000,
          commission_kes: 30000,
          adjustments_kes: -10000,
          effective_kes: 20000,
          config_version: 1,
          adjustments: [
            {
              id: 'adj-1',
              kind: 'REDUCTION',
              amount_kes: -10000,
              reason: 'Late',
              by_platform_admin: true,
              source_dispute_id: null,
              created_at: '',
            },
          ],
          created_at: '2026-10-02T08:00:00Z',
        },
      ]),
      totals: { records: 1, commission_kes: 30000, adjustments_kes: -10000, effective_kes: 20000 },
      statements_available: true,
    });
    renderWithProviders(<CommissionPage />);

    expect(await screen.findByRole('link', { name: 'ABC123' })).toHaveAttribute(
      'href',
      '/jobs/job-1',
    );
    expect(screen.getByRole('link', { name: 'Open statements' })).toHaveAttribute(
      'href',
      '/ops/statements',
    );
    expect(screen.getAllByText('KSh 200').length).toBeGreaterThan(0);
    expect(screen.getByText(/Reduced/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /pay/i })).not.toBeInTheDocument();
  });
});
