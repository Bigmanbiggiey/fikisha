import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/renderWithProviders';

import { BusinessesPage } from './BusinessesPage';

const listBusinesses = vi.fn();
const createBusiness = vi.fn();

vi.mock('./orgApi', () => ({
  orgApi: {
    listBusinesses: (...a: unknown[]) => listBusinesses(...a),
    createBusiness: (...a: unknown[]) => createBusiness(...a),
  },
}));

// AuthProvider calls authApi.me() on mount — keep it anonymous & quiet.
vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: () => Promise.reject(new Error('anon')), logout: vi.fn() },
}));

describe('BusinessesPage', () => {
  beforeEach(() => {
    listBusinesses.mockReset();
    createBusiness.mockReset();
  });

  it('lists the businesses I belong to', async () => {
    listBusinesses.mockResolvedValue({
      data: [{ id: 'b1', trading_name: 'Mama Njeri Hardware', standing: 'GOOD', my_role: 'OWNER' }],
      page: { next_cursor: null, prev_cursor: null },
    });
    renderWithProviders(<BusinessesPage />);
    expect(await screen.findByText('Mama Njeri Hardware')).toBeInTheDocument();
    expect(screen.getByText('OWNER')).toBeInTheDocument();
  });

  it('creates a business and refreshes the list', async () => {
    listBusinesses.mockResolvedValueOnce({
      data: [],
      page: { next_cursor: null, prev_cursor: null },
    });
    createBusiness.mockResolvedValue({ id: 'b2', trading_name: 'New Co' });
    listBusinesses.mockResolvedValueOnce({
      data: [{ id: 'b2', trading_name: 'New Co', standing: 'GOOD', my_role: 'OWNER' }],
      page: { next_cursor: null, prev_cursor: null },
    });

    renderWithProviders(<BusinessesPage />);
    await screen.findByText(/not a member of any business/i);

    await userEvent.type(screen.getByLabelText(/trading name/i), 'New Co');
    await userEvent.click(screen.getByRole('button', { name: /^create$/i }));

    await waitFor(() => expect(createBusiness).toHaveBeenCalledWith({ trading_name: 'New Co' }));
    expect(await screen.findByText('New Co')).toBeInTheDocument();
  });
});
