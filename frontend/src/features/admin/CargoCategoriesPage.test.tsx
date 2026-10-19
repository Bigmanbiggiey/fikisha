import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/renderWithProviders';

import { CargoCategoriesPage } from './CargoCategoriesPage';

const uncategorisedCargo = vi.fn();
const addCargoKeyword = vi.fn();
const addCargoCategory = vi.fn();
const cargoCategories = vi.fn();

vi.mock('./adminApi', () => ({
  adminApi: {
    uncategorisedCargo: (...a: unknown[]) => uncategorisedCargo(...a),
    addCargoKeyword: (...a: unknown[]) => addCargoKeyword(...a),
    addCargoCategory: (...a: unknown[]) => addCargoCategory(...a),
  },
}));
vi.mock('@/features/jobs/jobsApi', () => ({
  jobsApi: { cargoCategories: (...a: unknown[]) => cargoCategories(...a) },
}));
vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: () => Promise.reject(new Error('anon')), logout: vi.fn() },
}));

describe('CargoCategoriesPage (assessment 2026-10-19 D-5)', () => {
  beforeEach(() => {
    uncategorisedCargo.mockResolvedValue({
      data: [{ description: 'Mitungi ya gesi', count: 2, last_seen: '2026-10-19T06:00:00Z' }],
    });
    cargoCategories.mockResolvedValue({
      data: [
        { code: 'LIQUIDS_BULK', latent_risk: false },
        { code: 'OTHER', latent_risk: false },
      ],
    });
    addCargoKeyword.mockResolvedValue({ version: 9 });
  });

  it('lists what could not be placed and teaches a keyword', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CargoCategoriesPage />);
    expect(await screen.findByText('Mitungi ya gesi')).toBeInTheDocument();
    expect(screen.getByText(/2 jobs/)).toBeInTheDocument();
    // Other is never offered as a target.
    expect(screen.queryByRole('option', { name: 'Other' })).not.toBeInTheDocument();

    const keyword = screen.getByLabelText('Keyword');
    await user.clear(keyword);
    await user.type(keyword, 'gesi');
    await user.click(screen.getByRole('button', { name: 'Add keyword' }));
    await waitFor(() =>
      expect(addCargoKeyword).toHaveBeenCalledWith({
        category_code: 'LIQUIDS_BULK',
        keyword: 'gesi',
        rationale: 'Taught from the uncategorised list',
      }),
    );
    expect(await screen.findByText('Added "gesi" to Fuel and bulk liquids.')).toBeInTheDocument();
  });
});
