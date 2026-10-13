import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '@/features/auth/AuthProvider';
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
        { id: 'g2', name: 'Drives for', my_role: 'DRIVER', assignment_mode: 'DRIVER_ACCEPTS' },
      ],
      page: { next_cursor: null, prev_cursor: null },
    });

    renderWithProviders(<Probe />);

    expect(await screen.findByText('BUSINESS:Mama Njeri Hardware')).toBeInTheDocument();
    expect(screen.getByText('OPERATOR:A. Otieno')).toBeInTheDocument();
    expect(screen.getByText('GROUP_MANAGER:Kitengela Yard')).toBeInTheDocument();
    expect(screen.getByText('OPERATIONS_OFFICER:Operations')).toBeInTheDocument();
    // A DRIVER membership is a Driver workspace, not a Group Manager one
    // (Design Phase 7 P-04, founder ruling 2026-09-28):
    expect(screen.getByText('DRIVER:Drives for')).toBeInTheDocument();
    expect(screen.queryByText('GROUP_MANAGER:Drives for')).not.toBeInTheDocument();
    // not a party to b2, not a platform admin:
    expect(screen.queryByText(/Not mine/)).not.toBeInTheDocument();
    expect(screen.queryByText(/PLATFORM_ADMIN/)).not.toBeInTheDocument();
  });

  it("never shows the previous user's operator profile to the next person on the same tab", async () => {
    // One query cache, two sign-ins (sign-out doesn't clear the cache).
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const renderShared = (): ReturnType<typeof render> =>
      render(
        <QueryClientProvider client={client}>
          <MemoryRouter>
            <AuthProvider>
              <Probe />
            </AuthProvider>
          </MemoryRouter>
        </QueryClientProvider>,
      );
    const user = (id: string): Record<string, unknown> => ({
      id, phone: '+254700000001', display_name: id, locale: 'en', status: 'ACTIVE', roles: [], is_admin: false,
    });
    listBusinesses.mockResolvedValue({ data: [], page: { next_cursor: null, prev_cursor: null } });
    listGroups.mockResolvedValue({ data: [], page: { next_cursor: null, prev_cursor: null } });

    meMock.mockResolvedValue(user('u1'));
    getMyOperator.mockResolvedValue({ id: 'op1', full_name: 'First Person', display_name: '' });
    const first = renderShared();
    expect(await screen.findByText('OPERATOR:First Person')).toBeInTheDocument();
    first.unmount();

    meMock.mockResolvedValue(user('u2'));
    getMyOperator.mockRejectedValue(
      new ApiError({ type: 'about:blank', title: 'Not Found', status: 404, code: 'not_found', detail: '' }, 404, 'not found'),
    );
    renderShared();
    await waitFor(() => expect(getMyOperator).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(screen.queryByText('loading')).not.toBeInTheDocument());
    expect(screen.queryByText(/OPERATOR:/)).not.toBeInTheDocument();
  });

  it('asks for the operator profile once, however many readers mount (no 404 loop)', async () => {
    // Regression (10c re-capture): with the 404 kept as an error, each newly
    // mounted reader re-fetched it and flipped everything back to loading,
    // in a loop, for anyone without an operator profile.
    meMock.mockResolvedValue({
      id: 'u1', phone: '+254700000001', display_name: 'B', locale: 'en', status: 'ACTIVE', roles: [], is_admin: false,
    });
    listBusinesses.mockResolvedValue({
      data: [{ id: 'b1', trading_name: 'Mama Njeri Hardware', my_role: 'OWNER' }],
      page: { next_cursor: null, prev_cursor: null },
    });
    getMyOperator.mockRejectedValue(
      new ApiError({ type: 'about:blank', title: 'Not Found', status: 404, code: 'not_found', detail: '' }, 404, 'not found'),
    );
    listGroups.mockResolvedValue({ data: [], page: { next_cursor: null, prev_cursor: null } });

    function Late(): JSX.Element {
      const { loading } = useWorkspaces();
      return <p>{loading ? 'late loading' : 'late ready'}</p>;
    }
    function Readers(): JSX.Element {
      const { loading } = useWorkspaces();
      // More readers mount only once the first has settled, as the shell's
      // tab bar, sidebar and page do.
      return <>{loading ? <p>loading</p> : [1, 2, 3].map((i) => <Late key={i} />)}</>;
    }
    renderWithProviders(<Readers />);

    expect(await screen.findAllByText('late ready')).toHaveLength(3);
    await new Promise((r) => setTimeout(r, 50));
    expect(screen.queryByText('loading')).not.toBeInTheDocument();
    expect(getMyOperator).toHaveBeenCalledTimes(1);
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
  it('gives an Ops Officer (who also has is_admin, like every AdminProfile) no Platform Admin workspace', async () => {
    // Regression (Design Phase 6 Increment 8): the backend sets is_admin for
    // any active AdminProfile, so an Ops Officer has it too — it must not be
    // read as 'Platform Admin'.
    meMock.mockResolvedValue({
      id: 'u1',
      phone: '+254700000008',
      display_name: 'Ops',
      locale: 'en',
      status: 'ACTIVE',
      roles: ['OPERATIONS_OFFICER'],
      is_admin: true,
    });
    listBusinesses.mockResolvedValue({ data: [], page: { next_cursor: null, prev_cursor: null } });
    getMyOperator.mockRejectedValue(
      new ApiError({ type: 'about:blank', title: 'Not Found', status: 404, code: 'not_found', detail: '' }, 404, 'not found'),
    );
    listGroups.mockResolvedValue({ data: [], page: { next_cursor: null, prev_cursor: null } });

    renderWithProviders(<Probe />);
    expect(await screen.findByText('OPERATIONS_OFFICER:Operations')).toBeInTheDocument();
    expect(screen.queryByText(/PLATFORM_ADMIN/)).not.toBeInTheDocument();
  });
});
