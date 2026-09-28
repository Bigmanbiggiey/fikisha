import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Route, Routes } from 'react-router-dom';

import { ApiError } from '@/services/problem';
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
const notes = vi.fn();
const addNote = vi.fn();
const revealContacts = vi.fn();

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
vi.mock('@/features/ops/opsApi', () => ({
  notesQueryKey: (jobId: string) => ['job-notes', jobId],
  opsApi: {
    notes: (...a: unknown[]) => notes(...a),
    addNote: (...a: unknown[]) => addNote(...a),
    revealContacts: (...a: unknown[]) => revealContacts(...a),
    events: () => Promise.resolve({ data: [] }),
  },
}));
vi.mock('./geo', () => ({ getOneShotGeo: () => Promise.resolve(undefined) }));
const getVehicle = vi.fn();
vi.mock('@/features/vehicles/vehiclesApi', () => ({
  vehiclesApi: { get: (...a: unknown[]) => getVehicle(...a) },
}));
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
    notes.mockReset();
    addNote.mockReset();
    revealContacts.mockReset();
    notes.mockResolvedValue({ data: [] });
    meMock.mockRejectedValue(new Error('anon'));
    getVehicle.mockReset();
    getVehicle.mockRejectedValue(new Error('forbidden'));
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

  it('never cancels on one tap: the sheet needs a reason, then cancels with it', async () => {
    get.mockResolvedValue(
      baseJob({ status: 'CONFIRMED', next_allowed_statuses: ['ASSIGNED', 'CANCELLED'] }),
    );
    cancel.mockResolvedValue({ ...baseJob({ status: 'CANCELLED' }) });

    const user = userEvent.setup();
    renderAtJob('01a0a4123456');

    await user.click(await screen.findByRole('button', { name: 'Cancel request' }));
    expect(cancel).not.toHaveBeenCalled();

    const confirm = screen.getByRole('button', { name: 'Cancel the job' });
    expect(confirm).toBeDisabled();
    expect(screen.getByText(/doesn’t count against you/)).toBeInTheDocument();

    await user.click(screen.getByLabelText('We didn’t agree on price'));
    await user.click(confirm);

    await waitFor(() =>
      expect(cancel).toHaveBeenCalledWith(
        '01a0a4123456',
        { reason_code: 'PRICE_DISAGREEMENT', reason_text: undefined },
        expect.any(String),
      ),
    );
  });

  it.each([
    ['ASSIGNED', /late cancellation/],
    ['AT_PICKUP', /wasted trip/],
  ])('warns about the consequence of cancelling at %s before confirming', async (status, text) => {
    get.mockResolvedValue(baseJob({ status, next_allowed_statuses: ['CANCELLED'] }));
    const user = userEvent.setup();
    renderAtJob('01a0a4123456');

    await user.click(await screen.findByRole('button', { name: 'Cancel request' }));
    expect(screen.getByText(text)).toBeInTheDocument();
    expect(cancel).not.toHaveBeenCalled();
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

  it('clears a failed attempt\'s error when the sheet is reopened', async () => {
    get.mockResolvedValue(baseJob({ status: 'ASSIGNED', next_allowed_statuses: ['CANCELLED'] }));
    cancel.mockRejectedValue(new Error('conflict'));
    const user = userEvent.setup();
    renderAtJob('01a0a4123456');

    await user.click(await screen.findByRole('button', { name: 'Cancel request' }));
    await user.click(screen.getByLabelText('My plans changed'));
    await user.click(screen.getByRole('button', { name: 'Cancel the job' }));
    expect(await screen.findByText('Something went wrong. Please try again.')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Keep the job' }));
    await user.click(screen.getByRole('button', { name: 'Cancel request' }));

    expect(screen.getByRole('button', { name: 'Cancel the job' })).toBeDisabled();
    expect(screen.queryByText('Something went wrong. Please try again.')).not.toBeInTheDocument();
  });

  it('does not offer the business Cancel on a DISPUTED job (admin-only there)', async () => {
    get.mockResolvedValue(
      baseJob({ status: 'DISPUTED', next_allowed_statuses: ['CANCELLED', 'COMPLETED', 'FAILED'] }),
    );
    renderAtJob('01a0a4123456');

    // Wait for the loaded page (the route), then check.
    expect(await screen.findByText('Depot, Kitengela')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Cancel request' })).not.toBeInTheDocument();
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
      // Not the driver: the ordinary page, not the driver's Current job.
      expect(screen.queryByText('Full job detail')).not.toBeInTheDocument();
      expect(screen.queryByRole('link', { name: /^Call/ })).not.toBeInTheDocument();
    });

    describe('as the assigned driver (Current job, P-03)', () => {
      function driverJob(overrides: Record<string, unknown> = {}): Record<string, unknown> {
        return baseJob({
          status: 'ASSIGNED',
          assigned_driver_id: 'op1',
          assigned_vehicle_id: 'veh1',
          next_allowed_statuses: ['AT_PICKUP', 'CANCELLED', 'FAILED'],
          pickup_location: {
            address_text: 'Depot, Kitengela',
            lat: null,
            lng: null,
            contact_name: 'Mary W.',
            contact_phone: '0712 345 678',
          },
          destination_location: { address_text: 'Shop 4, Kitengela', lat: '-1.47', lng: '36.96', contact_name: '', contact_phone: '' },
          recipient_name: 'J. Mwangi',
          recipient_phone: '+254 733 111 222',
          ...overrides,
        });
      }

      it('shows the driver view with a driver-voiced line, not the business wording', async () => {
        get.mockResolvedValue(driverJob());
        renderAtJob('01a0a4123456');

        expect(await screen.findByRole('heading', { name: 'Job 123456' })).toBeInTheDocument();
        expect(screen.getByText('Head to pickup. Tap the button below when you get there.')).toBeInTheDocument();
        expect(screen.queryByText('A driver has been assigned and is on the way to pickup.')).not.toBeInTheDocument();
        expect(screen.getByRole('button', { name: "I'm at pickup" })).toHaveClass('min-h-target-driver');
        expect(screen.getByText('Full job detail')).toBeInTheDocument();
      });

      it('links both contacts by phone, sender first before pickup', async () => {
        get.mockResolvedValue(driverJob());
        renderAtJob('01a0a4123456');

        const call = await screen.findAllByRole('link', { name: /^Call/ });
        expect(call.map((a) => a.getAttribute('href'))).toEqual(['tel:0712345678', 'tel:+254733111222']);
        expect(screen.getByRole('link', { name: 'Call Mary W.' })).toBeInTheDocument();
        expect(screen.getByRole('link', { name: 'WhatsApp Mary W.' })).toHaveAttribute(
          'href',
          'https://wa.me/254712345678',
        );
        expect(screen.getByRole('link', { name: /Go to pickup/ })).toHaveAttribute(
          'href',
          'https://www.google.com/maps/search/?api=1&query=Depot%2C%20Kitengela',
        );
        expect(screen.getByRole('link', { name: /Go to drop-off/ })).toHaveAttribute(
          'href',
          'https://www.google.com/maps/search/?api=1&query=-1.47%2C36.96',
        );
      });

      it('puts the receiver first once the goods are collected', async () => {
        get.mockResolvedValue(
          driverJob({
            status: 'IN_TRANSIT',
            next_allowed_statuses: ['AT_DESTINATION'],
            timestamps: { ...(baseJob().timestamps as object), picked_up_at: '2026-09-15T11:00:00Z' },
          }),
        );
        renderAtJob('01a0a4123456');

        const call = await screen.findAllByRole('link', { name: /^Call/ });
        expect(call[0]).toHaveAccessibleName('Call J. Mwangi');
        expect(screen.getByText('Transit').closest('li')).toHaveAttribute('aria-current', 'step');
      });

      it('offers Call but no WhatsApp for a number it cannot read as Kenyan, and says when none was given', async () => {
        get.mockResolvedValue(
          driverJob({
            recipient_phone: '+44 7700 900123',
            recipient_name: 'Visitor',
            pickup_location: { address_text: 'Depot', lat: null, lng: null, contact_name: 'Mary W.', contact_phone: '' },
          }),
        );
        renderAtJob('01a0a4123456');

        expect(await screen.findByRole('link', { name: 'Call Visitor' })).toHaveAttribute('href', 'tel:+447700900123');
        expect(screen.queryByRole('link', { name: 'WhatsApp Visitor' })).not.toBeInTheDocument();
        expect(screen.getByText(/No number given/)).toBeInTheDocument();
        expect(screen.queryByRole('link', { name: 'Call Mary W.' })).not.toBeInTheDocument();
      });

      it('never pairs the recipient name with the drop-off contact number', async () => {
        get.mockResolvedValue(
          driverJob({
            recipient_name: 'J. Mwangi',
            recipient_phone: '',
            destination_location: {
              address_text: 'Shop 4',
              lat: null,
              lng: null,
              contact_name: 'Shop manager',
              contact_phone: '0722 999 888',
            },
          }),
        );
        renderAtJob('01a0a4123456');

        await screen.findByRole('link', { name: 'Call Mary W.' });
        expect(screen.queryByRole('link', { name: 'Call J. Mwangi' })).not.toBeInTheDocument();
        expect(screen.queryByRole('link', { name: /0722|Shop manager/ })).not.toBeInTheDocument();
        expect(screen.getAllByText(/No number given/)).toHaveLength(1);
      });

      it('shows the vehicle when it can be read, and leaves it out when refused', async () => {
        getVehicle.mockResolvedValue({ id: 'veh1', registration: 'KDA 200B', vehicle_class: 'PICKUP' });
        get.mockResolvedValue(driverJob());
        const { unmount } = renderAtJob('01a0a4123456');
        expect(await screen.findByText('KDA 200B · PICKUP')).toBeInTheDocument();
        expect(getVehicle).toHaveBeenCalledWith('veh1');
        unmount();

        getVehicle.mockRejectedValue(new Error('forbidden'));
        renderAtJob('01a0a4123456');
        await screen.findByRole('heading', { name: 'Job 123456' });
        await waitFor(() => expect(getVehicle).toHaveBeenCalledTimes(2));
        expect(screen.queryByText('Vehicle')).not.toBeInTheDocument();
      });

      it('puts a DISPUTED job on hold with no lifecycle action', async () => {
        get.mockResolvedValue(driverJob({ status: 'DISPUTED', next_allowed_statuses: ['CANCELLED', 'COMPLETED', 'FAILED'] }));
        renderAtJob('01a0a4123456');

        expect(await screen.findByText('This job is on hold — Fikisha is reviewing an issue.')).toBeInTheDocument();
        expect(screen.queryByRole('button', { name: "I'm at pickup" })).not.toBeInTheDocument();
        expect(screen.getByRole('link', { name: '· Report an issue' })).toBeInTheDocument();
      });

      it('says "Delivery recorded" once DELIVERED', async () => {
        get.mockResolvedValue(
          driverJob({
            status: 'DELIVERED',
            next_allowed_statuses: ['COMPLETED', 'DISPUTED'],
            timestamps: {
              ...(baseJob().timestamps as object),
              picked_up_at: '2026-09-15T11:00:00Z',
              delivered_at: '2026-09-15T12:00:00Z',
            },
          }),
        );
        renderAtJob('01a0a4123456');

        expect(await screen.findByText('Delivery recorded')).toBeInTheDocument();
        // All three progress steps done; none current. (Scoped to the
        // progress list: the full timeline in the disclosure has its own.)
        const progress = screen.getByText('Progress').parentElement!;
        expect(within(progress).queryByRole('listitem', { current: 'step' })).not.toBeInTheDocument();
        expect(within(progress).getAllByTitle('done')).toHaveLength(3);
      });
    });
  });
  it('shows Fikisha operational notes to a job party', async () => {
    get.mockResolvedValue(baseJob());
    notes.mockResolvedValue({
      data: [{ id: 'n1', text: 'Driver is 20 minutes late', created_at: '2026-09-23T08:00:00Z', author_label: 'Fikisha Operations' }],
    });
    renderAtJob('01a0a4123456');
    expect(await screen.findByText('Updates from Fikisha')).toBeInTheDocument();
    expect(screen.getByText('Driver is 20 minutes late')).toBeInTheDocument();
  });

  describe('as Fikisha staff', () => {
    function signInAs(roles: string[]): void {
      meMock.mockResolvedValue({
        id: 's1', phone: '+254700000008', display_name: 'Ops', locale: 'en', status: 'ACTIVE', roles, is_admin: true,
      });
      listBusinesses.mockResolvedValue({ data: [], page: { next_cursor: null, prev_cursor: null } });
      getMyOperator.mockRejectedValue(
        new ApiError({ type: 'about:blank', title: 'Not Found', status: 404, code: 'not_found', detail: '' }, 404, 'not found'),
      );
      listGroups.mockResolvedValue({ data: [], page: { next_cursor: null, prev_cursor: null } });
    }

    it('renders the staff panel instead of the business actions', async () => {
      signInAs(['OPERATIONS_OFFICER']);
      get.mockResolvedValue(baseJob({ value_band: 'STANDARD' }));
      renderAtJob('01a0a4123456');
      expect(await screen.findByRole('heading', { name: 'Fikisha Operations' })).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Cancel request' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Confirm pickup' })).not.toBeInTheDocument();
    });

    it('lets an Ops Officer cancel a STANDARD job only with a reason', async () => {
      signInAs(['OPERATIONS_OFFICER']);
      get.mockResolvedValue(baseJob({ value_band: 'STANDARD' }));
      cancel.mockResolvedValue(baseJob({ status: 'CANCELLED' }));
      const user = userEvent.setup();
      renderAtJob('01a0a4123456');

      await user.click(await screen.findByRole('button', { name: 'Cancel this job' }));
      const confirm = screen.getByRole('button', { name: 'Cancel the job' });
      expect(confirm).toBeDisabled();
      await user.type(screen.getByLabelText('Reason for cancelling'), 'Business asked by phone');
      await user.click(confirm);
      expect(cancel).toHaveBeenCalledWith(
        '01a0a4123456',
        { reason_code: 'ADMIN_ACTION', reason_text: 'Business asked by phone' },
        expect.any(String),
      );
    });

    it('replaces cancel with the Platform-Admin notice above the Standard band', async () => {
      signInAs(['OPERATIONS_OFFICER']);
      get.mockResolvedValue(baseJob({ value_band: 'ELEVATED' }));
      renderAtJob('01a0a4123456');
      expect(await screen.findByText(/Cancelling this job needs a Platform Administrator/)).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Cancel this job' })).not.toBeInTheDocument();
    });

    it('offers cancel above the Standard band to a Platform Admin', async () => {
      signInAs(['PLATFORM_ADMIN']);
      get.mockResolvedValue(baseJob({ value_band: 'VERY_HIGH' }));
      renderAtJob('01a0a4123456');
      expect(await screen.findByRole('button', { name: 'Cancel this job' })).toBeInTheDocument();
    });

    it('reveals contacts only on request', async () => {
      signInAs(['OPERATIONS_OFFICER']);
      get.mockResolvedValue(baseJob({ value_band: 'STANDARD' }));
      revealContacts.mockResolvedValue({
        job_id: '01a0a4123456',
        contacts: {
          business: null, pickup: { name: 'Juma', phone: '+254700900001' }, destination: null,
          recipient: null, operator: null, driver: null,
        },
      });
      const user = userEvent.setup();
      renderAtJob('01a0a4123456');

      await user.click(await screen.findByRole('button', { name: 'Show contact details' }));
      expect(revealContacts).toHaveBeenCalledTimes(1);
      expect(await screen.findByRole('link', { name: '+254700900001' })).toHaveAttribute('href', 'tel:+254700900001');
    });
  });
});
