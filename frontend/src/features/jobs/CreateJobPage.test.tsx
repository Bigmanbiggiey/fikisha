import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/services/problem';
import { renderWithProviders } from '@/test/renderWithProviders';

import { CreateJobPage } from './CreateJobPage';

const create = vi.fn();
const submit = vi.fn();
const listBusinesses = vi.fn();
const getMyOperator = vi.fn();
const listGroups = vi.fn();
const reference = vi.fn();

vi.mock('./jobsApi', () => ({
  jobsApi: {
    create: (...a: unknown[]) => create(...a),
    submit: (...a: unknown[]) => submit(...a),
  },
}));
vi.mock('@/features/org/orgApi', () => ({
  orgApi: {
    listBusinesses: (...a: unknown[]) => listBusinesses(...a),
    getMyOperator: (...a: unknown[]) => getMyOperator(...a),
    listGroups: (...a: unknown[]) => listGroups(...a),
  },
}));
vi.mock('@/features/diagnostics/diagnosticsApi', () => ({
  diagnosticsApi: { reference: (...a: unknown[]) => reference(...a) },
}));
vi.mock('@/features/auth/authApi', () => ({
  authApi: {
    me: () =>
      Promise.resolve({
        id: 'u1',
        phone: '+254700000001',
        display_name: 'Owner',
        locale: 'en',
        status: 'ACTIVE',
        roles: [],
        is_admin: false,
      }),
    logout: vi.fn(),
  },
}));

async function fillAndAdvance(user: ReturnType<typeof userEvent.setup>, label: RegExp, value: string): Promise<void> {
  await user.type(screen.getByLabelText(label), value);
  await user.click(screen.getByRole('button', { name: 'Next' }));
}

describe('CreateJobPage', () => {
  beforeEach(() => {
    create.mockReset();
    submit.mockReset();
    listBusinesses.mockResolvedValue({
      data: [{ id: 'b1', trading_name: 'Mama Njeri Hardware', my_role: 'OWNER' }],
      page: { next_cursor: null, prev_cursor: null },
    });
    getMyOperator.mockRejectedValue(
      new ApiError(
        { type: 'about:blank', title: 'Not Found', status: 404, code: 'not_found', detail: '' },
        404,
        'not found',
      ),
    );
    listGroups.mockResolvedValue({ data: [], page: { next_cursor: null, prev_cursor: null } });
    reference.mockResolvedValue({
      locales: { supported: ['en', 'sw'], default: 'en', operator_default: 'sw' },
      config_version: 1,
      vehicle_types: ['PICKUP', 'LORRY'],
    });
  });

  it('walks all 8 steps, reviews, and sends the request', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CreateJobPage />, { route: '/jobs/new' });

    expect(await screen.findByText('Step 1 of 8')).toBeInTheDocument();

    await fillAndAdvance(user, /Pickup location/, 'Depot, Kitengela');
    expect(await screen.findByText('Step 2 of 8')).toBeInTheDocument();

    await user.type(screen.getByLabelText(/Destination/), 'Shop 4, Kitengela');
    await user.type(screen.getByLabelText(/Recipient name/), 'J. Mwangi');
    await user.click(screen.getByRole('button', { name: 'Next' }));
    expect(await screen.findByText('Step 3 of 8')).toBeInTheDocument();

    await fillAndAdvance(user, /Description/, '20 cartons of electronics');
    expect(await screen.findByText('Step 4 of 8')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Next' })); // weight/size optional
    expect(await screen.findByText('Step 5 of 8')).toBeInTheDocument();

    await fillAndAdvance(user, /approximate value/, '12000');
    expect(await screen.findByText('Step 6 of 8')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Next' })); // vehicle optional
    expect(await screen.findByText('Step 7 of 8')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Next' })); // when — ASAP default
    expect(await screen.findByText('Step 8 of 8')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Review request' }));
    expect(await screen.findByText('Draft — not sent yet')).toBeInTheDocument();
    expect(screen.getByText('20 cartons of electronics')).toBeInTheDocument();

    create.mockResolvedValue({ id: 'job123' });
    submit.mockResolvedValue({ id: 'job123', status: 'REQUESTED' });

    await user.click(screen.getByRole('button', { name: 'Send request' }));

    await waitFor(() => expect(submit).toHaveBeenCalled());
    expect(create).toHaveBeenCalledWith(
      'b1',
      expect.objectContaining({
        pickup_location: expect.objectContaining({ address_text: 'Depot, Kitengela' }),
        destination_location: expect.objectContaining({
          address_text: 'Shop 4, Kitengela',
          contact_name: 'J. Mwangi',
        }),
        cargo: expect.objectContaining({
          description: '20 cartons of electronics',
          declared_value_kes: 1_200_000,
        }),
      }),
      expect.any(String),
    );
    expect(submit).toHaveBeenCalledWith('job123', expect.any(String));
  });
});
