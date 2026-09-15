import { screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/services/problem';
import { renderWithProviders } from '@/test/renderWithProviders';

import { useWorkspaces } from './useWorkspaces';

const meMock = vi.fn();
const listBusinesses = vi.fn();
const getMyOperator = vi.fn();
const listGroups = vi.fn();

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

function Probe(): JSX.Element {
  const { loading, workspaces } = useWorkspaces();
  if (loading) return <div>loading</div>;
  return (
    <ul>
      {workspaces.map((w) => (
        <li key={`${w.kind}:${w.id ?? ''}`}>{`${w.kind}:${w.label}`}</li>
      ))}
    </ul>
  );
}

describe('useWorkspaces', () => {
  beforeEach(() => {
    meMock.mockReset();
    listBusinesses.mockReset();
    getMyOperator.mockReset();
    listGroups.mockReset();
  });

  it('reports no workspaces (and never calls the org APIs) while signed out', async () => {
    meMock.mockRejectedValue(new Error('anon'));
    renderWithProviders(<Probe />);
    await waitFor(() => expect(screen.queryByText('loading')).not.toBeInTheDocument());
    expect(screen.getByRole('list')).toBeEmptyDOMElement();
    expect(listBusinesses).not.toHaveBeenCalled();
  });

  it('resolves every workspace a signed-in user actually holds', async () => {
    meMock.mockResolvedValue({
      id: 'u1',
      phone: '+254700000001',
      display_name: 'A. Otieno',
      locale: 'en',
      status: 'ACTIVE',
      roles: ['OPERATIONS_OFFICER'],
      is_admin: false,
    });
    listBusinesses.mockResolvedValue({
      data: [
        { id: 'b1', trading_name: 'Mama Njeri Hardware', my_role: 'OWNER' },
        { id: 'b2', trading_name: 'Not mine', my_role: null },
      ],
      page: { next_cursor: null, prev_cursor: null },
    });
    getMyOperator.mockResolvedValue({
      id: 'op1',
      full_name: 'A. Otieno',
      display_name: '',
    });
    listGroups.mockResolvedValue({
      data: [
        { id: 'g1', name: 'Kitengela Yard', my_role: 'MANAGER' },
        { id: 'g2', name: 'Not managed', my_role: 'DRIVER' },
      ],
      page: { next_cursor: null, prev_cursor: null },
    });

    renderWithProviders(<Probe />);

    expect(await screen.findByText('BUSINESS:Mama Njeri Hardware')).toBeInTheDocument();
    expect(screen.getByText('OPERATOR:A. Otieno')).toBeInTheDocument();
    expect(screen.getByText('GROUP_MANAGER:Kitengela Yard')).toBeInTheDocument();
    expect(screen.getByText('OPERATIONS_OFFICER:Operations')).toBeInTheDocument();
    // not a party to b2, not a manager/owner of g2 (DRIVER-only), not a platform admin:
    expect(screen.queryByText(/Not mine/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Not managed/)).not.toBeInTheDocument();
    expect(screen.queryByText(/PLATFORM_ADMIN/)).not.toBeInTheDocument();
  });

  it('treats a 404 from getMyOperator as "no operator profile", not an error', async () => {
    meMock.mockResolvedValue({
      id: 'u1',
      phone: '+254700000001',
      display_name: 'B',
      locale: 'en',
      status: 'ACTIVE',
      roles: [],
      is_admin: false,
    });
    listBusinesses.mockResolvedValue({ data: [], page: { next_cursor: null, prev_cursor: null } });
    getMyOperator.mockRejectedValue(
      new ApiError({ type: 'about:blank', title: 'Not Found', status: 404, code: 'not_found', detail: '' }, 404, 'not found'),
    );
    listGroups.mockResolvedValue({ data: [], page: { next_cursor: null, prev_cursor: null } });

    renderWithProviders(<Probe />);
    await waitFor(() => expect(screen.queryByText('loading')).not.toBeInTheDocument());
    expect(screen.getByRole('list')).toBeEmptyDOMElement();
  });
});
