import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Route, Routes } from 'react-router-dom';

import { renderWithProviders } from '@/test/renderWithProviders';

import { JobDetailPage } from './JobDetailPage';

/** `JobDetailPage` reads `:jobId` via `useParams()` — `renderWithProviders`
 * only supplies a bare `MemoryRouter` (no route table), so the component
 * under test must itself be wrapped in the `Route` that supplies the param,
 * same as it's mounted for real in `app/router.tsx`. */
function renderAtJob(jobId: string): ReturnType<typeof renderWithProviders> {
  return renderWithProviders(
    <Routes>
      <Route path="/jobs/:jobId" element={<JobDetailPage />} />
      <Route path="/jobs/:jobId/negotiation" element={<div>Negotiation screen</div>} />
      <Route path="/jobs/:jobId/pickup-proof" element={<div>Pickup proof screen</div>} />
      <Route path="/jobs/:jobId/delivery-proof" element={<div>Delivery proof screen</div>} />
      <Route path="/jobs/:jobId/report-issue" element={<div>Report issue screen</div>} />
      <Route path="/disputes/:disputeId" element={<div>Dispute screen</div>} />
    </Routes>,
    { route: `/jobs/${jobId}` },
  );
}

const get = vi.fn();
const cancel = vi.fn();
const arrivePickup = vi.fn();
const startTransit = vi.fn();
const arriveDestination = vi.fn();
const meMock = vi.fn();
const listBusinesses = vi.fn();
const getMyOperator = vi.fn();
const listGroups = vi.fn();
const listDisputesForJob = vi.fn();

vi.mock('./jobsApi', () => ({
  jobsApi: {
    get: (...a: unknown[]) => get(...a),
    cancel: (...a: unknown[]) => cancel(...a),
    submit: vi.fn(),
    arrivePickup: (...a: unknown[]) => arrivePickup(...a),
    startTransit: (...a: unknown[]) => startTransit(...a),
    arriveDestination: (...a: unknown[]) => arriveDestination(...a),
  },
}));
vi.mock('@/features/incidents/incidentsApi', () => ({
  disputesApi: { listForJob: (...a: unknown[]) => listDisputesForJob(...a) },
}));
vi.mock('./geo', () => ({ getOneShotGeo: () => Promise.resolve(undefined) }));
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

function baseJob(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: '01a0a4123456',
    business_id: 'biz1',
    status: 'AT_PICKUP',
    version: 1,
    next_allowed_statuses: ['PICKED_UP', 'CANCELLED', 'FAILED', 'DISPUTED'],
    pickup_location: { address_text: 'Depot, Kitengela' },
    destination_location: { address_text: 'Shop 4, Kitengela' },
    recipient_name: 'J. Mwangi',
    cargo: { description: '20 cartons', handling_flags: [] },
    agreed_price_kes: 250_000,
    proposed_price_kes: null,
    timestamps: {
      created_at: null,
      published_at: '2026-09-15T10:00:00Z',
      confirmed_at: '2026-09-15T10:05:00Z',
      assigned_at: '2026-09-15T10:10:00Z',
      picked_up_at: null,
      delivered_at: null,
      completed_at: null,
      terminal_at: null,
    },
    ...overrides,
  };
}

describe('JobDetailPage', () => {
  beforeEach(() => {
    get.mockReset();
    cancel.mockReset();
    arrivePickup.mockReset();
    startTransit.mockReset();
    arriveDestination.mockReset();
    meMock.mockReset();
    listBusinesses.mockReset();
    getMyOperator.mockReset();
    listGroups.mockReset();
    listDisputesForJob.mockReset();
    listDisputesForJob.mockResolvedValue({ data: [] });
    meMock.mockRejectedValue(new Error('anon'));
  });

  it('shows the status header, next action, and route for an AT_PICKUP job', async () => {
    get.mockResolvedValue(baseJob());
    renderAtJob('01a0a4123456');

    // "At pickup" legitimately appears twice (the status chip and the
    // current timeline step) — assert via the unique status-line role
    // instead of the ambiguous chip text. Wait for the button first so the
    // (also role="status") PageLoader spinner isn't the one matched.
    expect(await screen.findByRole('button', { name: 'Confirm pickup' })).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('The driver is collecting your goods.');
    expect(screen.getByText('Depot, Kitengela')).toBeInTheDocument();
  });

  it('shows "nothing needed" for a state with no business action, and offers Cancel', async () => {
    get.mockResolvedValue(
      baseJob({ status: 'ASSIGNED', next_allowed_statuses: ['AT_PICKUP', 'CANCELLED', 'FAILED'] }),
    );
    renderAtJob('01a0a4123456');

    expect(await screen.findByText('Nothing needed from you right now.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cancel request' })).toBeInTheDocument();
  });

  it('cancels the job on confirmation', async () => {
    get.mockResolvedValue(
      baseJob({ status: 'CONFIRMED', next_allowed_statuses: ['ASSIGNED', 'CANCELLED'] }),
    );
    cancel.mockResolvedValue({ ...baseJob({ status: 'CANCELLED' }) });

    const user = userEvent.setup();
    renderAtJob('01a0a4123456');

    const cancelButton = await screen.findByRole('button', { name: 'Cancel request' });
    await user.click(cancelButton);

    expect(cancel).toHaveBeenCalledWith(
      '01a0a4123456',
      { reason_code: 'BUSINESS_CHANGED_MIND' },
      expect.any(String),
    );
  });

  it('navigates to the negotiation thread from "Review offers" while NEGOTIATING', async () => {
    get.mockResolvedValue(
      baseJob({ status: 'NEGOTIATING', next_allowed_statuses: ['CONFIRMED', 'CANCELLED'] }),
    );
    const user = userEvent.setup();
    renderAtJob('01a0a4123456');

    await user.click(await screen.findByRole('button', { name: 'Review offers' }));
    expect(await screen.findByText('Negotiation screen')).toBeInTheDocument();
  });

  it('does not show Cancel once the job cannot be cancelled', async () => {
    get.mockResolvedValue(baseJob({ status: 'COMPLETED', next_allowed_statuses: ['DISPUTED'] }));
    renderAtJob('01a0a4123456');

    await screen.findByText('Nothing needed from you right now.');
    expect(screen.queryByRole('button', { name: 'Cancel request' })).not.toBeInTheDocument();
  });

  it('keeps prior timeline steps marked done when a job is DISPUTED', async () => {
    get.mockResolvedValue(
      baseJob({
        status: 'DISPUTED',
        next_allowed_statuses: [],
        timestamps: {
          created_at: null,
          published_at: '2026-09-15T10:00:00Z',
          confirmed_at: '2026-09-15T10:05:00Z',
          assigned_at: '2026-09-15T10:10:00Z',
          picked_up_at: '2026-09-15T10:20:00Z',
          delivered_at: null,
          completed_at: null,
          terminal_at: null,
        },
      }),
    );
    renderAtJob('01a0a4123456');

    await screen.findByText('Depot, Kitengela');

    // Regression: `happyPathIndex('DISPUTED')` is -1 (DISPUTED isn't a
    // happy-path status), which used to make every step render as
    // 'upcoming' instead of keeping the progress made before the dispute.
    // "Picked up" has a timestamp, so it must still show its checkmark...
    const pickedUpRow = screen.getByText('Picked up').closest('li');
    expect(pickedUpRow?.querySelector('.bg-status-success-solid')).toBeInTheDocument();
    // ...but "In transit" never happened and must not be marked done.
    const inTransitRow = screen.getByText('In transit').closest('li');
    expect(inTransitRow?.querySelector('.bg-status-success-solid')).not.toBeInTheDocument();
  });

  it('links to the real dispute once one exists for a DISPUTED job', async () => {
    get.mockResolvedValue(baseJob({ status: 'DISPUTED', next_allowed_statuses: [] }));
    listDisputesForJob.mockResolvedValue({ data: [{ id: 'dis1', job_id: '01a0a4123456' }] });
    const user = userEvent.setup();
    renderAtJob('01a0a4123456');

    await user.click(await screen.findByRole('button', { name: 'View dispute' }));
    expect(await screen.findByText('Dispute screen')).toBeInTheDocument();
  });

  it('falls back to "coming in a later update" if a DISPUTED job somehow has no dispute row', async () => {
    get.mockResolvedValue(baseJob({ status: 'DISPUTED', next_allowed_statuses: [] }));
    listDisputesForJob.mockResolvedValue({ data: [] });
    renderAtJob('01a0a4123456');

    expect(await screen.findByText('This screen is coming in a later update.')).toBeInTheDocument();
  });

  it('offers "Report an issue" once the job is no longer a DRAFT', async () => {
    get.mockResolvedValue(baseJob({ status: 'ASSIGNED' }));
    const user = userEvent.setup();
    renderAtJob('01a0a4123456');

    await user.click(await screen.findByText('· Report an issue'));
    expect(await screen.findByText('Report issue screen')).toBeInTheDocument();
  });

  it('hides "Report an issue" while the job is still a DRAFT', async () => {
    get.mockResolvedValue(baseJob({ status: 'DRAFT', next_allowed_statuses: ['REQUESTED'] }));
    renderAtJob('01a0a4123456');

    await screen.findByText('Continue request');
    expect(screen.queryByText('· Report an issue')).not.toBeInTheDocument();
  });

  describe('as the operator viewer', () => {
    beforeEach(() => {
      // The operator holds no Business workspace that owns this job's
      // business_id ('biz1'), so useJobViewerRole resolves 'OPERATOR'.
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

    it('shows a role-aware NEGOTIATING line, not the business-authored default', async () => {
      // Regression: the default NEGOTIATING line ("An operator has
      // responded — review their offer.") is written from the business's
      // point of view — nonsensical for the operator who just responded
      // and is waiting on the business. Found live (Design Phase 6
      // Increment 4 verification).
      get.mockResolvedValue(baseJob({ status: 'NEGOTIATING', next_allowed_statuses: ['CONFIRMED', 'CANCELLED'] }));
      renderAtJob('01a0a4123456');

      expect(await screen.findByText('Waiting for the business to respond to your offer.')).toBeInTheDocument();
      expect(screen.queryByText('An operator has responded — review their offer.')).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Respond' })).toBeInTheDocument();
    });

    it('offers "Assign driver & vehicle" once CONFIRMED', async () => {
      get.mockResolvedValue(baseJob({ status: 'CONFIRMED', next_allowed_statuses: ['ASSIGNED', 'CANCELLED'] }));
      renderAtJob('01a0a4123456');

      expect(await screen.findByRole('button', { name: 'Assign driver & vehicle' })).toBeInTheDocument();
      // Operator-side cancel is out of scope this increment (a different
      // reason code and consequence screen) — the Business cancel button
      // must not render for this viewer.
      expect(screen.queryByRole('button', { name: 'Cancel request' })).not.toBeInTheDocument();
    });

    it('calls arrivePickup when the assigned driver taps "I\'m at pickup" while ASSIGNED', async () => {
      get.mockResolvedValue(
        baseJob({
          status: 'ASSIGNED',
          assigned_driver_id: 'op1',
          next_allowed_statuses: ['AT_PICKUP', 'CANCELLED', 'FAILED'],
        }),
      );
      arrivePickup.mockResolvedValue({ ...baseJob({ status: 'AT_PICKUP' }) });
      const user = userEvent.setup();
      renderAtJob('01a0a4123456');

      await user.click(await screen.findByRole('button', { name: "I'm at pickup" }));
      expect(arrivePickup).toHaveBeenCalledWith('01a0a4123456', undefined, expect.any(String));
    });

    it('navigates to the pickup-proof screen from "Confirm pickup" while AT_PICKUP', async () => {
      get.mockResolvedValue(
        baseJob({
          status: 'AT_PICKUP',
          assigned_driver_id: 'op1',
          next_allowed_statuses: ['PICKED_UP', 'FAILED'],
        }),
      );
      const user = userEvent.setup();
      renderAtJob('01a0a4123456');

      await user.click(await screen.findByRole('button', { name: 'Confirm pickup' }));
      expect(await screen.findByText('Pickup proof screen')).toBeInTheDocument();
    });

    it('calls startTransit when the assigned driver taps "Start transit" while PICKED_UP', async () => {
      get.mockResolvedValue(
        baseJob({
          status: 'PICKED_UP',
          assigned_driver_id: 'op1',
          next_allowed_statuses: ['IN_TRANSIT'],
        }),
      );
      startTransit.mockResolvedValue({ ...baseJob({ status: 'IN_TRANSIT' }) });
      const user = userEvent.setup();
      renderAtJob('01a0a4123456');

      await user.click(await screen.findByRole('button', { name: 'Start transit' }));
      expect(startTransit).toHaveBeenCalledWith('01a0a4123456', expect.any(String));
    });

    it('calls arriveDestination when the assigned driver taps "I\'ve arrived" while IN_TRANSIT', async () => {
      get.mockResolvedValue(
        baseJob({
          status: 'IN_TRANSIT',
          assigned_driver_id: 'op1',
          next_allowed_statuses: ['AT_DESTINATION'],
        }),
      );
      arriveDestination.mockResolvedValue({ ...baseJob({ status: 'AT_DESTINATION' }) });
      const user = userEvent.setup();
      renderAtJob('01a0a4123456');

      await user.click(await screen.findByRole('button', { name: "I've arrived" }));
      expect(arriveDestination).toHaveBeenCalledWith('01a0a4123456', undefined, expect.any(String));
    });

    it('navigates to the delivery-proof screen from "Confirm delivery" while AT_DESTINATION', async () => {
      get.mockResolvedValue(
        baseJob({
          status: 'AT_DESTINATION',
          assigned_driver_id: 'op1',
          next_allowed_statuses: ['DELIVERED'],
        }),
      );
      const user = userEvent.setup();
      renderAtJob('01a0a4123456');

      await user.click(await screen.findByRole('button', { name: 'Confirm delivery' }));
      expect(await screen.findByText('Delivery proof screen')).toBeInTheDocument();
    });

    it('is read-only once ASSIGNED if the operator is not the assigned driver', async () => {
      get.mockResolvedValue(
        baseJob({
          status: 'ASSIGNED',
          assigned_driver_id: 'someone-else',
          next_allowed_statuses: ['AT_PICKUP', 'CANCELLED', 'FAILED'],
        }),
      );
      renderAtJob('01a0a4123456');

      expect(await screen.findByText('Nothing needed from you right now.')).toBeInTheDocument();
    });
  });
});
