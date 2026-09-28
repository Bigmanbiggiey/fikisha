import { screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/renderWithProviders';

import { useActiveRole } from './activeRole';
import type { Workspace } from './workspaces';

let workspaces: Workspace[] = [];
const listVehicles = vi.fn();

vi.mock('./useWorkspaces', () => ({
  useWorkspaces: () => ({ loading: false, workspaces }),
}));
vi.mock('@/features/vehicles/vehiclesApi', () => ({
  vehiclesApi: { list: (...a: unknown[]) => listVehicles(...a) },
}));
vi.mock('@/features/auth/authApi', () => ({
  authApi: {
    me: () =>
      Promise.resolve({ id: 'u1', phone: '+254700000001', display_name: 'A', locale: 'en', status: 'ACTIVE', roles: [], is_admin: false }),
    logout: vi.fn(),
  },
}));

function Probe(): JSX.Element {
  const { loading, roles, role } = useActiveRole();
  if (loading) return <p>loading</p>;
  return <p>{`${roles.join(',')}|${role ?? 'none'}`}</p>;
}

const operator: Workspace = { kind: 'OPERATOR', id: 'op1', label: 'A. Otieno' };
const groupDriver: Workspace = { kind: 'DRIVER', id: 'g1', label: 'Yard', assignmentMode: 'MANAGER_ASSIGNS' };

describe('navigation roles (Design Phase 7 P-04, founder ruling 2026-09-28)', () => {
  beforeEach(() => {
    listVehicles.mockReset();
    window.localStorage.clear();
  });

  it('a solo operator gets the Operator navigation, with no vehicle lookup', async () => {
    workspaces = [operator];
    renderWithProviders(<Probe />);
    expect(await screen.findByText('OPERATOR|OPERATOR')).toBeInTheDocument();
    expect(listVehicles).not.toHaveBeenCalled();
  });

  it('a group driver who owns no vehicle gets the Driver navigation only', async () => {
    workspaces = [operator, groupDriver];
    listVehicles.mockResolvedValue({ data: [{ id: 'v1', owner_operator_id: null, owner_group_id: 'g1' }] });
    renderWithProviders(<Probe />);
    expect(await screen.findByText('DRIVER|DRIVER')).toBeInTheDocument();
  });

  it('a group driver who also owns a vehicle gets both, Operator first', async () => {
    workspaces = [operator, groupDriver];
    listVehicles.mockResolvedValue({ data: [{ id: 'v1', owner_operator_id: 'op1', owner_group_id: null }] });
    renderWithProviders(<Probe />);
    expect(await screen.findByText('OPERATOR,DRIVER|OPERATOR')).toBeInTheDocument();
  });

  it('Platform Admin wins over Operations, and a business comes first by default', async () => {
    workspaces = [
      { kind: 'OPERATIONS_OFFICER', id: null, label: 'Operations' },
      { kind: 'PLATFORM_ADMIN', id: null, label: 'Platform Admin' },
      { kind: 'BUSINESS', id: 'b1', label: 'Mama Njeri' },
    ];
    renderWithProviders(<Probe />);
    expect(await screen.findByText('BUSINESS,PLATFORM_ADMIN|BUSINESS')).toBeInTheDocument();
  });

  it('remembers the chosen role per person, and ignores one they no longer have', async () => {
    workspaces = [{ kind: 'BUSINESS', id: 'b1', label: 'Mama Njeri' }, operator];
    window.localStorage.setItem('fikisha.activeRole.u1', 'OPERATOR');
    const { unmount } = renderWithProviders(<Probe />);
    expect(await screen.findByText('BUSINESS,OPERATOR|OPERATOR')).toBeInTheDocument();
    unmount();

    window.localStorage.setItem('fikisha.activeRole.u1', 'PLATFORM_ADMIN');
    renderWithProviders(<Probe />);
    await waitFor(() => expect(screen.getByText('BUSINESS,OPERATOR|BUSINESS')).toBeInTheDocument());
  });
});
