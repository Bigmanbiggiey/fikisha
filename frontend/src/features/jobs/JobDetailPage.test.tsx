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
    </Routes>,
    { route: `/jobs/${jobId}` },
  );
}

const get = vi.fn();
const cancel = vi.fn();

vi.mock('./jobsApi', () => ({
  jobsApi: {
    get: (...a: unknown[]) => get(...a),
    cancel: (...a: unknown[]) => cancel(...a),
    submit: vi.fn(),
  },
}));
vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: () => Promise.reject(new Error('anon')), logout: vi.fn() },
}));

function baseJob(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: '01a0a4123456',
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
});
