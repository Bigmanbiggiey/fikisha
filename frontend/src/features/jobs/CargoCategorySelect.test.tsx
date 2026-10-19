import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/renderWithProviders';

import { CargoCategorySelect } from './CargoCategorySelect';

const cargoCategories = vi.fn();
const suggestCargoCategory = vi.fn();

vi.mock('./jobsApi', () => ({
  jobsApi: {
    cargoCategories: (...a: unknown[]) => cargoCategories(...a),
    suggestCargoCategory: (...a: unknown[]) => suggestCargoCategory(...a),
  },
}));
vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: () => Promise.reject(new Error('anon')), logout: vi.fn() },
}));

function Harness(): JSX.Element {
  const [description, setDescription] = useState('');
  const [code, setCode] = useState('');
  return (
    <>
      <label>
        Description
        <input value={description} onChange={(e) => setDescription(e.target.value)} />
      </label>
      <CargoCategorySelect aria-label="Category" value={code} onChange={setCode} description={description} />
      <output>{code || 'none'}</output>
    </>
  );
}

describe('CargoCategorySelect (assessment 2026-10-19 D-5)', () => {
  beforeEach(() => {
    cargoCategories.mockResolvedValue({
      data: [
        { code: 'CONSTRUCTION_MATERIALS', latent_risk: false },
        { code: 'ELECTRONICS', latent_risk: true },
        { code: 'OTHER', latent_risk: false },
      ],
    });
    suggestCargoCategory.mockImplementation((text: string) =>
      Promise.resolve({ code: /cement/i.test(text) ? 'CONSTRUCTION_MATERIALS' : null }),
    );
  });

  it('fills itself in from the description, in the person’s language', async () => {
    const user = userEvent.setup();
    renderWithProviders(<Harness />);
    expect(await screen.findByRole('option', { name: 'Construction materials' })).toBeInTheDocument();
    await user.type(screen.getByLabelText('Description'), '20 bags of cement');
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('CONSTRUCTION_MATERIALS'), {
      timeout: 2000,
    });
    expect(screen.getByLabelText('Category', { selector: 'select' })).toHaveValue('CONSTRUCTION_MATERIALS');
    expect(screen.getByText('Chosen from your description. You can change it.')).toBeInTheDocument();
  });

  it('stops following the description once the person picks', async () => {
    const user = userEvent.setup();
    renderWithProviders(<Harness />);
    await screen.findByRole('option', { name: 'Electronics' });
    await user.selectOptions(screen.getByLabelText('Category', { selector: 'select' }), 'ELECTRONICS');
    await user.type(screen.getByLabelText('Description'), '20 bags of cement');
    await new Promise((r) => setTimeout(r, 600));
    expect(screen.getByRole('status')).toHaveTextContent('ELECTRONICS');
  });
});
