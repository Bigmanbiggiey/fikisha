import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/renderWithProviders';

import { VehiclesPage } from './VehiclesPage';

const list = vi.fn();
const create = vi.fn();
const getMyOperator = vi.fn();
const listGroups = vi.fn();

vi.mock('./vehiclesApi', async (orig) => {
  const actual = await orig<typeof import('./vehiclesApi')>();
  return {
    ...actual,
    vehiclesApi: {
      list: (...a: unknown[]) => list(...a),
      create: (...a: unknown[]) => create(...a),
    },
  };
});
vi.mock('@/features/org/orgApi', () => ({
  orgApi: {
    getMyOperator: (...a: unknown[]) => getMyOperator(...a),
    listGroups: (...a: unknown[]) => listGroups(...a),
  },
}));
vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: () => Promise.reject(new Error('anon')), logout: vi.fn() },
}));

describe('VehiclesPage', () => {
  beforeEach(() => {
    list.mockReset();
    create.mockReset();
    getMyOperator.mockResolvedValue({ id: 'op1', full_name: 'Me' });
    listGroups.mockResolvedValue({ data: [], page: { next_cursor: null, prev_cursor: null } });
  });

  it('lists my vehicles', async () => {
    list.mockResolvedValue({
      data: [
        {
          id: 'v1',
          registration: 'KAA 123A',
          vehicle_class: 'PICKUP',
          vehicle_class_heavy: false,
          controller_kind: 'OPERATOR',
          status: 'ACTIVE',
        },
      ],
      page: { next_cursor: null, prev_cursor: null },
    });
    renderWithProviders(<VehiclesPage />);
    expect(await screen.findByText(/KAA 123A · PICKUP/)).toBeInTheDocument();
  });

  it('registers a vehicle to my operator profile', async () => {
    list.mockResolvedValueOnce({ data: [], page: { next_cursor: null, prev_cursor: null } });
    create.mockResolvedValue({ id: 'v2' });
    list.mockResolvedValueOnce({
      data: [
        {
          id: 'v2',
          registration: 'KBB 9Z',
          vehicle_class: 'LORRY',
          vehicle_class_heavy: true,
          controller_kind: 'OPERATOR',
          status: 'INACTIVE',
        },
      ],
      page: { next_cursor: null, prev_cursor: null },
    });

    renderWithProviders(<VehiclesPage />);
    await screen.findByText(/no vehicles yet/i);

    await userEvent.type(screen.getByLabelText(/registration number/i), 'KBB 9Z');
    await userEvent.type(screen.getByLabelText(/capacity/i), '8');
    await userEvent.click(screen.getByRole('button', { name: /^create$/i }));

    await waitFor(() =>
      expect(create).toHaveBeenCalledWith(
        expect.objectContaining({ registration: 'KBB 9Z', owner_operator_id: 'op1' }),
      ),
    );
  });
});
