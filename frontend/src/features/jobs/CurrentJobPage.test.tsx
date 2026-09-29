import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Route, Routes } from 'react-router-dom';

import { renderWithProviders } from '@/test/renderWithProviders';
import type { Workspace } from '@/shell/workspaces';

import { CurrentJobPage } from './CurrentJobPage';

const list = vi.fn();
let workspaces: Workspace[] = [];
let roles: string[] = ['DRIVER'];

vi.mock('./jobsApi', () => ({ jobsApi: { list: (...a: unknown[]) => list(...a) } }));
vi.mock('@/shell/useWorkspaces', () => ({ useWorkspaces: () => ({ loading: false, workspaces }) }));
vi.mock('@/shell/activeRole', () => ({
  useActiveRole: () => ({ loading: false, roles, role: roles[0], setRole: vi.fn() }),
}));
vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: () => Promise.reject(new Error('anon')), logout: vi.fn() },
}));

function job(id: string, status: string, driver = 'op1'): Record<string, unknown> {
  return {
    id,
    status,
    assigned_driver_id: driver,
    pickup_location: { address_text: 'Depot' },
    destination_location: { address_text: 'Shop 4' },
    cargo: { description: 'Cartons' },
  };
}

function renderPage(): void {
  renderWithProviders(
    <Routes>
      <Route path="/current-job" element={<CurrentJobPage />} />
      <Route path="/jobs/:jobId" element={<div>Job screen</div>} />
    </Routes>,
    { route: '/current-job' },
  );
}

const operator: Workspace = { kind: 'OPERATOR', id: 'op1', label: 'A' };

describe('CurrentJobPage (Design Phase 7 P-04)', () => {
  beforeEach(() => {
    list.mockReset();
    roles = ['DRIVER'];
    workspaces = [operator, { kind: 'DRIVER', id: 'g1', label: 'Yard', assignmentMode: 'MANAGER_ASSIGNS' }];
  });

  it("opens the driver's one current job", async () => {
    list.mockResolvedValue({ data: [job('j1', 'COMPLETED'), job('j2', 'IN_TRANSIT'), job('j3', 'ASSIGNED', 'someone-else')] });
    renderPage();
    expect(await screen.findByText('Job screen')).toBeInTheDocument();
  });

  it('lists several current jobs to choose from', async () => {
    list.mockResolvedValue({ data: [job('jobaaa111', 'ASSIGNED'), job('jobbbb222', 'DISPUTED')] });
    renderPage();
    expect(await screen.findByText('You have 2 current jobs. Choose one.')).toBeInTheDocument();
    expect(screen.getByText('AAA111')).toBeInTheDocument();
    expect(screen.getByText('BBB222')).toBeInTheDocument();
  });

  it('with none, a MANAGER_ASSIGNS group driver is told they will be notified, with no work link', async () => {
    list.mockResolvedValue({ data: [job('j1', 'DELIVERED')] });
    renderPage();
    expect(await screen.findByText('No active job')).toBeInTheDocument();
    expect(screen.getByText("You'll be notified when you're assigned a job.")).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'See available work' })).not.toBeInTheDocument();
  });

  it('with none, a DRIVER_ACCEPTS group driver gets the available-work link', async () => {
    workspaces = [operator, { kind: 'DRIVER', id: 'g1', label: 'Yard', assignmentMode: 'DRIVER_ACCEPTS' }];
    list.mockResolvedValue({ data: [] });
    renderPage();
    expect(await screen.findByRole('link', { name: 'See available work' })).toHaveAttribute('href', '/work');
  });

  it('with none, an individual operator gets the available-work link', async () => {
    roles = ['OPERATOR', 'DRIVER'];
    list.mockResolvedValue({ data: [] });
    renderPage();
    expect(await screen.findByRole('link', { name: 'See available work' })).toBeInTheDocument();
  });
});
