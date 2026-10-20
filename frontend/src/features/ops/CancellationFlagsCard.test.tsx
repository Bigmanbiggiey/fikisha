import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/renderWithProviders';

import { CancellationFlagsCard } from './CancellationFlagsCard';

const cancellationFlags = vi.fn();
const reviewCancellationFlag = vi.fn();

vi.mock('./opsApi', () => ({
  opsApi: {
    cancellationFlags: (...a: unknown[]) => cancellationFlags(...a),
    reviewCancellationFlag: (...a: unknown[]) => reviewCancellationFlag(...a),
  },
}));

beforeEach(() => {
  cancellationFlags.mockReset();
  reviewCancellationFlag.mockReset().mockResolvedValue({ id: 'f1', status: 'CLEARED' });
});

describe('cancellation flags (trust plan A7)', () => {
  it('stays hidden with no open flag', async () => {
    cancellationFlags.mockResolvedValue({ data: [] });
    const { container } = renderWithProviders(<CancellationFlagsCard />);
    await new Promise((r) => setTimeout(r, 20));
    expect(container).toBeEmptyDOMElement();
  });

  it('staff clear a flag with a note', async () => {
    cancellationFlags.mockResolvedValue({
      data: [{ id: 'f1', business_id: 'b1', business_name: 'Mama Mboga Ltd', count: 3, created_at: '2026-10-20T08:00:00Z' }],
    });
    const u = userEvent.setup();
    renderWithProviders(<CancellationFlagsCard />);
    expect(await screen.findByText('Mama Mboga Ltd')).toBeInTheDocument();
    expect(screen.getByText(/3 late cancellations or wasted trips in 30 days/)).toBeInTheDocument();
    await u.click(screen.getByRole('button', { name: 'Clear' }));
    await u.type(screen.getByLabelText('Reason'), 'Spoke to the owner; seasonal stock.');
    await u.click(screen.getByRole('button', { name: 'Continue' }));
    await u.click(screen.getAllByRole('button', { name: 'Clear' }).at(-1)!);
    expect(reviewCancellationFlag).toHaveBeenCalledWith('f1', {
      outcome: 'CLEARED',
      note: 'Spoke to the owner; seasonal stock.',
    });
  });
});
