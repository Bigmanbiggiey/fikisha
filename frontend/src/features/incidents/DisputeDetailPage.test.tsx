import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Route, Routes } from 'react-router-dom';

import { renderWithProviders } from '@/test/renderWithProviders';

import { DisputeDetailPage } from './DisputeDetailPage';

const getDispute = vi.fn();
const getJob = vi.fn();
const listIncidentsForJob = vi.fn();
const meMock = vi.fn();

vi.mock('./incidentsApi', () => ({
  disputesApi: {
    get: (...a: unknown[]) => getDispute(...a),
    resolve: vi.fn(),
  },
  incidentsApi: {
    listForJob: (...a: unknown[]) => listIncidentsForJob(...a),
  },
}));
vi.mock('@/features/jobs/jobsApi', () => ({
  jobsApi: { get: (...a: unknown[]) => getJob(...a) },
}));
vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: (...a: unknown[]) => meMock(...a), logout: vi.fn() },
}));

function renderAtDispute(disputeId: string): ReturnType<typeof renderWithProviders> {
  return renderWithProviders(
    <Routes>
      <Route path="/disputes/:disputeId" element={<DisputeDetailPage />} />
    </Routes>,
    { route: `/disputes/${disputeId}` },
  );
}

function baseDispute(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: 'dis1',
    job_id: 'job1',
    incident_ids: ['inc1'],
    status: 'OPEN',
    pre_dispute_status: 'AT_DESTINATION',
    created_at: '2026-09-20T10:00:00Z',
    resolution: null,
    ...overrides,
  };
}

function baseJob(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return { id: 'job1', value_band: 'STANDARD', ...overrides };
}

describe('DisputeDetailPage', () => {
  beforeEach(() => {
    getDispute.mockReset();
    getJob.mockReset();
    listIncidentsForJob.mockReset();
    meMock.mockReset();
    listIncidentsForJob.mockResolvedValue({ data: [] });
  });

  it('a non-admin party gets a read-only view, no resolve form', async () => {
    meMock.mockRejectedValue(new Error('anon'));
    getDispute.mockResolvedValue(baseDispute());
    getJob.mockResolvedValue(baseJob());
    renderAtDispute('dis1');

    expect(await screen.findByText("Fikisha is reviewing this. You'll be notified when it's resolved.")).toBeInTheDocument();
    expect(screen.queryByText('Resolve this dispute')).not.toBeInTheDocument();
  });

  it('an Ops Officer on a STANDARD-band dispute sees the resolve form without commission-treatment controls', async () => {
    meMock.mockResolvedValue({
      id: 'u1', phone: '+254700000001', display_name: 'Ops', locale: 'en', status: 'ACTIVE',
      roles: ['OPERATIONS_OFFICER'], is_admin: true,
    });
    getDispute.mockResolvedValue(baseDispute());
    getJob.mockResolvedValue(baseJob({ value_band: 'STANDARD' }));
    renderAtDispute('dis1');

    expect(await screen.findByText('Resolve this dispute')).toBeInTheDocument();
    expect(screen.queryByText('Commission treatment')).not.toBeInTheDocument();
    // No Resume shell for an Ops Officer, regardless of band.
    expect(screen.queryByText('Resume when the authoritative system permits it — not available yet.')).not.toBeInTheDocument();
  });

  it('an Ops Officer on an above-STANDARD dispute sees the escalation exception, not resolve controls', async () => {
    meMock.mockResolvedValue({
      id: 'u1', phone: '+254700000001', display_name: 'Ops', locale: 'en', status: 'ACTIVE',
      roles: ['OPERATIONS_OFFICER'], is_admin: true,
    });
    getDispute.mockResolvedValue(baseDispute());
    getJob.mockResolvedValue(baseJob({ value_band: 'ELEVATED' }));
    renderAtDispute('dis1');

    expect(await screen.findByText('This needs a Platform Administrator.')).toBeInTheDocument();
    expect(screen.queryByText('Resolve this dispute')).not.toBeInTheDocument();
  });

  it('a Platform Admin sees full resolve controls plus the permanently-disabled Resume shell', async () => {
    meMock.mockResolvedValue({
      id: 'u2', phone: '+254700000002', display_name: 'Admin', locale: 'en', status: 'ACTIVE',
      roles: ['PLATFORM_ADMIN'], is_admin: true,
    });
    getDispute.mockResolvedValue(baseDispute());
    getJob.mockResolvedValue(baseJob({ value_band: 'VERY_HIGH' }));
    renderAtDispute('dis1');

    expect(await screen.findByText('Commission treatment')).toBeInTheDocument();
    const resumeButton = await screen.findByRole('button', { name: 'Resume this Job to At destination' });
    expect(resumeButton).toBeDisabled();
    expect(
      screen.getByText('Resume when the authoritative system permits it — not available yet.'),
    ).toBeInTheDocument();
  });
});
