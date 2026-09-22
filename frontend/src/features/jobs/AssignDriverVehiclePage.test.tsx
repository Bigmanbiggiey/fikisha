import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Route, Routes } from 'react-router-dom';

import { ApiError } from '@/services/problem';
import { renderWithProviders } from '@/test/renderWithProviders';

import { AssignDriverVehiclePage } from './AssignDriverVehiclePage';

const get = vi.fn();
const assignmentCandidates = vi.fn();
const assign = vi.fn();

vi.mock('./jobsApi', () => ({
  jobsApi: {
    get: (...a: unknown[]) => get(...a),
    assignmentCandidates: (...a: unknown[]) => assignmentCandidates(...a),
    assign: (...a: unknown[]) => assign(...a),
  },
}));
vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: () => Promise.reject(new Error('anon')), logout: vi.fn() },
}));

function renderAtJob(jobId: string): ReturnType<typeof renderWithProviders> {
  return renderWithProviders(
    <Routes>
      <Route path="/jobs/:jobId/assign" element={<AssignDriverVehiclePage />} />
      <Route path="/jobs/:jobId" element={<div>Job detail screen</div>} />
    </Routes>,
    { route: `/jobs/${jobId}/assign` },
  );
}

function baseCandidates(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    job_id: 'job1',
    value_band: 'STANDARD',
    supports_group_assignment: false,
    blocked: null,
    drivers: [{ id: 'drv1', name: 'D. Kamau', trust_level: 'L1', eligible: true, reasons: [] }],
    vehicles: [
      {
        id: 'veh1',
        registration: 'KDA 200B',
        vehicle_class: 'PICKUP',
        capacity_value: '2000',
        capacity_unit: 'KG',
        status: 'ACTIVE',
        eligible: true,
        reasons: [],
      },
    ],
    ...overrides,
  };
}

describe('AssignDriverVehiclePage', () => {
  beforeEach(() => {
    get.mockReset();
    assignmentCandidates.mockReset();
    assign.mockReset();
    get.mockResolvedValue({ id: 'job1', status: 'CONFIRMED' });
  });

  it('auto-selects the sole eligible driver and submits the assignment', async () => {
    assignmentCandidates.mockResolvedValue(baseCandidates());
    assign.mockResolvedValue({ id: 'job1', status: 'ASSIGNED' });
    const user = userEvent.setup();
    renderAtJob('job1');

    await user.click(await screen.findByRole('radio', { name: /KDA 200B/ }));
    await user.click(screen.getByRole('button', { name: 'Confirm assignment' }));

    expect(assign).toHaveBeenCalledWith(
      'job1',
      { driver_profile_id: 'drv1', vehicle_id: 'veh1' },
      expect.any(String),
    );
    expect(await screen.findByText('Job detail screen')).toBeInTheDocument();
  });

  it('on a server rejection, shows the reason and refetches candidates instead of forcing the assignment', async () => {
    // Regression: the driver/vehicle looked eligible when the screen loaded
    // but the server is authoritative — a rejection must never be silently
    // retried or bypassed; the UI shows the reason and refreshes.
    assignmentCandidates.mockResolvedValue(baseCandidates());
    const user = userEvent.setup();
    renderAtJob('job1');

    await user.click(await screen.findByRole('radio', { name: /KDA 200B/ }));

    assign.mockRejectedValueOnce(
      new ApiError(
        {
          type: 'about:blank',
          title: 'Vehicle not eligible',
          status: 422,
          code: 'vehicle_not_eligible',
          detail: 'The vehicle is not active.',
        },
        422,
        'The vehicle is not active.',
      ),
    );
    const callsBeforeSubmit = assignmentCandidates.mock.calls.length;
    await user.click(screen.getByRole('button', { name: 'Confirm assignment' }));

    expect(await screen.findByText('The vehicle is not active.')).toBeInTheDocument();
    await waitFor(() =>
      expect(assignmentCandidates.mock.calls.length).toBeGreaterThan(callsBeforeSubmit),
    );
    // Never navigated away as if the assignment had succeeded.
    expect(screen.queryByText('Job detail screen')).not.toBeInTheDocument();
  });

  it('blocks submission and explains a pending high-value review', async () => {
    assignmentCandidates.mockResolvedValue(
      baseCandidates({ value_band: 'HIGH', blocked: "This job requires Fikisha's high-value review before it can be assigned." }),
    );
    renderAtJob('job1');

    expect(
      await screen.findByText("This job requires Fikisha's high-value review before it can be assigned."),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Confirm assignment' })).toBeDisabled();
  });
});
