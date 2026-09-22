import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Route, Routes } from 'react-router-dom';

import { renderWithProviders } from '@/test/renderWithProviders';

import { IncidentDetailPage } from './IncidentDetailPage';

const get = vi.fn();
const listDisputesForJob = vi.fn();
const startReview = vi.fn();
const escalate = vi.fn();
const meMock = vi.fn();

vi.mock('./incidentsApi', () => ({
  incidentsApi: {
    get: (...a: unknown[]) => get(...a),
    startReview: (...a: unknown[]) => startReview(...a),
    startAmicable: vi.fn(),
    escalate: (...a: unknown[]) => escalate(...a),
    evidenceBlob: vi.fn(),
  },
  disputesApi: {
    listForJob: (...a: unknown[]) => listDisputesForJob(...a),
    open: vi.fn(),
  },
}));
vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: (...a: unknown[]) => meMock(...a), logout: vi.fn() },
}));

function renderAtIncident(incidentId: string): ReturnType<typeof renderWithProviders> {
  return renderWithProviders(
    <Routes>
      <Route path="/incidents/:incidentId" element={<IncidentDetailPage />} />
    </Routes>,
    { route: `/incidents/${incidentId}` },
  );
}

function baseIncident(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: 'inc1',
    job_id: 'job1',
    type: 'DAMAGE',
    other_label: '',
    severity: '',
    status: 'OPEN',
    description: 'box was crushed',
    reported_by_kind: 'USER',
    created_at: '2026-09-20T10:00:00Z',
    evidence: [],
    statements: [],
    ...overrides,
  };
}

describe('IncidentDetailPage', () => {
  beforeEach(() => {
    get.mockReset();
    listDisputesForJob.mockReset();
    startReview.mockReset();
    escalate.mockReset();
    meMock.mockReset();
    listDisputesForJob.mockResolvedValue({ data: [] });
  });

  it('a non-admin party sees the incident context but no admin actions', async () => {
    meMock.mockRejectedValue(new Error('anon'));
    get.mockResolvedValue(baseIncident());
    renderAtIncident('inc1');

    expect(await screen.findByText('Damage')).toBeInTheDocument();
    expect(screen.queryByText('Review actions')).not.toBeInTheDocument();
  });

  it('an Ops Officer sees review actions but not the Platform-Admin-only escalate control', async () => {
    meMock.mockResolvedValue({
      id: 'u1', phone: '+254700000001', display_name: 'Ops', locale: 'en', status: 'ACTIVE',
      roles: ['OPERATIONS_OFFICER'], is_admin: true,
    });
    get.mockResolvedValue(baseIncident());
    const user = userEvent.setup();
    renderAtIncident('inc1');

    expect(await screen.findByRole('button', { name: 'Start review' })).toBeInTheDocument();
    expect(screen.queryByLabelText('Reason for escalating')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Start review' }));
    expect(startReview).toHaveBeenCalledWith('inc1');
  });

  it('a Platform Admin sees the escalate control too', async () => {
    meMock.mockResolvedValue({
      id: 'u2', phone: '+254700000002', display_name: 'Admin', locale: 'en', status: 'ACTIVE',
      roles: ['PLATFORM_ADMIN'], is_admin: true,
    });
    get.mockResolvedValue(baseIncident());
    renderAtIncident('inc1');

    expect(await screen.findByLabelText('Reason for escalating')).toBeInTheDocument();
  });
});
