import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/renderWithProviders';

import { MyTierCard } from './MyTierCard';
import { StaffTierPanel } from './StaffTierPanel';
import { TierCard } from './TierCard';
import type { TierView } from './types';

const meMock = vi.fn();
const api = { myTier: vi.fn(), tier: vi.fn(), setTier: vi.fn(), proposals: vi.fn(), decide: vi.fn() };

vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: (...a: unknown[]) => meMock(...a), logout: vi.fn() },
}));
vi.mock('./trustApi', () => ({
  trustApi: new Proxy(
    {},
    { get: (_t, key: string) => (...a: unknown[]) => api[key as keyof typeof api](...a) },
  ),
}));

function view(overrides: Partial<TierView> = {}): TierView {
  return {
    operator_id: 'op-1',
    operator_name: 'A. Dereva',
    level: 'L1',
    stored_level: 'L1',
    floor_met: true,
    since: null,
    bands: ['STANDARD'],
    max_value_kes: 5_000_000,
    next_level: 'L2',
    criteria: [
      { key: 'completed_jobs', status: 'NOT_MET', current: 5, target: 8 },
      { key: 'avg_rating', status: 'NOT_MEASURED', current: null, target: 4.2 },
      { key: 'good_conduct', status: 'MET', current: null, target: null },
    ],
    ready_for_review: false,
    open_proposal: null,
    history: [],
    ...overrides,
  };
}

const user = (roles: string[]) => ({
  id: 'u1',
  phone: '+254700000009',
  display_name: 'Someone',
  locale: 'en',
  status: 'ACTIVE',
  roles,
  is_admin: roles.length > 0,
});

beforeEach(() => {
  meMock.mockReset().mockResolvedValue(user([]));
  for (const fn of Object.values(api)) fn.mockReset();
});

describe('operator tier card (operator-tiers T-3)', () => {
  it('shows the tier, what it allows and the checklist toward the next tier', () => {
    renderWithProviders(<TierCard view={view()} />);
    expect(screen.getByText('L1 · Verified')).toBeInTheDocument();
    expect(screen.getByText('Jobs with goods worth up to KSh 50,000.')).toBeInTheDocument();
    expect(screen.getByText('Toward L2 · Established')).toBeInTheDocument();
    expect(screen.getByText(/Completed jobs: 5 of 8/)).toBeInTheDocument();
    expect(screen.getByText(/Average rating of 4.2 or more · not measured yet/)).toBeInTheDocument();
    expect(screen.getByText('No changes yet.')).toBeInTheDocument();
  });

  it('says when a review is under way, and shows reasons without staff names', () => {
    renderWithProviders(
      <TierCard
        view={view({
          open_proposal: {
            id: 'c1',
            from_level: 'L1',
            to_level: 'L2',
            trigger: 'AUTO_PROPOSED',
            status: 'PROPOSED',
            reason: '',
            created_at: '2026-10-20T08:00:00Z',
          },
          history: [
            {
              id: 'c0',
              from_level: 'L2',
              to_level: 'L1',
              trigger: 'ADMIN_OVERRIDE',
              status: 'APPLIED',
              reason: 'Two late cancellations this week.',
              created_at: '2026-10-19T08:00:00Z',
              by: 'Admin',
            },
          ],
        })}
      />,
    );
    expect(screen.getByText(/Fikisha is reviewing it/)).toBeInTheDocument();
    expect(screen.getByText(/Changed by Fikisha \(manual\)/)).toBeInTheDocument();
    expect(screen.getByText('Two late cancellations this week.')).toBeInTheDocument();
    expect(screen.queryByText(/Admin/)).not.toBeInTheDocument();
  });

  it('restricted and lapsed tiers explain themselves', () => {
    const { unmount } = renderWithProviders(
      <TierCard view={view({ level: 'RESTRICTED', stored_level: 'RESTRICTED', next_level: null, criteria: [] })} />,
    );
    expect(screen.getByText(/restricted you to smaller jobs/)).toBeInTheDocument();
    unmount();
    renderWithProviders(
      <TierCard view={view({ level: 'L0', stored_level: 'L2', floor_met: false, bands: [], max_value_kes: 0 })} />,
    );
    expect(screen.getByText(/No jobs yet: verification isn't complete./)).toBeInTheDocument();
    expect(screen.getByText(/Your tier is L2 · Established, but it applies only while/)).toBeInTheDocument();
  });

  it('Home shows a compact card linking to the progress', async () => {
    api.myTier.mockResolvedValue(view());
    renderWithProviders(<MyTierCard compact />);
    expect(await screen.findByRole('link', { name: 'See your progress toward L2 · Established' })).toHaveAttribute(
      'href',
      '/operator',
    );
    expect(screen.queryByText(/Completed jobs/)).not.toBeInTheDocument();
  });
});

describe('staff tier panel (operator-tiers T-4)', () => {
  it('an Operations Officer reads it but gets no controls', async () => {
    meMock.mockResolvedValue(user(['OPERATIONS_OFFICER']));
    api.tier.mockResolvedValue(view());
    renderWithProviders(<StaffTierPanel operatorId="op-1" />);
    expect(await screen.findByText('Tier')).toBeInTheDocument();
    await waitFor(() => expect(meMock).toHaveBeenCalled());
    expect(screen.queryByRole('button', { name: 'Change tier…' })).not.toBeInTheDocument();
  });

  it('a Platform Admin promotes with a reason', async () => {
    meMock.mockResolvedValue(user(['PLATFORM_ADMIN']));
    api.tier.mockResolvedValue(view());
    api.setTier.mockResolvedValue(view({ level: 'L3', stored_level: 'L3' }));
    const u = userEvent.setup();
    renderWithProviders(<StaffTierPanel operatorId="op-1" />);
    await u.selectOptions(await screen.findByLabelText('Change to'), 'L3');
    await u.click(screen.getByRole('button', { name: 'Change tier…' }));
    await u.type(screen.getByLabelText('Reason'), 'Long record at the Kitengela stage.');
    await u.click(screen.getByRole('button', { name: 'Continue' }));
    expect(screen.getByText(/Change A. Dereva from L1 · Verified to L3 · Trusted/)).toBeInTheDocument();
    await u.click(screen.getByRole('button', { name: 'Promote' }));
    await waitFor(() =>
      expect(api.setTier).toHaveBeenCalledWith('op-1', { level: 'L3', reason: 'Long record at the Kitengela stage.' }),
    );
  });

  it('a Platform Admin turns down a proposal', async () => {
    meMock.mockResolvedValue(user(['PLATFORM_ADMIN']));
    api.tier.mockResolvedValue(
      view({
        ready_for_review: true,
        open_proposal: {
          id: 'c1',
          from_level: 'L1',
          to_level: 'L2',
          trigger: 'AUTO_PROPOSED',
          status: 'PROPOSED',
          reason: '',
          created_at: '2026-10-20T08:00:00Z',
        },
      }),
    );
    api.decide.mockResolvedValue(view());
    const u = userEvent.setup();
    renderWithProviders(<StaffTierPanel operatorId="op-1" />);
    expect(await screen.findByText('Fikisha proposes L1 · Verified → L2 · Established.')).toBeInTheDocument();
    await u.click(screen.getByRole('button', { name: 'Not yet' }));
    await u.type(screen.getByLabelText('Reason'), 'Wait for the open complaint to close.');
    await u.click(screen.getByRole('button', { name: 'Continue' }));
    await u.click(screen.getAllByRole('button', { name: 'Not yet' }).at(-1)!);
    await waitFor(() =>
      expect(api.decide).toHaveBeenCalledWith('c1', { decision: 'REJECT', reason: 'Wait for the open complaint to close.' }),
    );
  });
});
