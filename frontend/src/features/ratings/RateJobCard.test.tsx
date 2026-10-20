import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/renderWithProviders';

import { RateJobCard } from './RateJobCard';

const forJob = vi.fn();
const submit = vi.fn();

vi.mock('./ratingsApi', () => ({
  ratingsQueryKey: (id: string) => ['jobs', id, 'ratings'],
  ratingsApi: {
    forJob: (...a: unknown[]) => forJob(...a),
    submit: (...a: unknown[]) => submit(...a),
  },
}));

beforeEach(() => {
  forJob.mockReset();
  submit.mockReset();
});

describe('rating a completed job (trust plan A4)', () => {
  it('the sender rates the operator with a score and an optional comment', async () => {
    forJob.mockResolvedValue({ can_rate: true, side: 'BUSINESS_RATES_OPERATOR', mine: null, about_me: null });
    submit.mockResolvedValue({
      can_rate: false,
      side: 'BUSINESS_RATES_OPERATOR',
      mine: { id: 'r1', side: 'BUSINESS_RATES_OPERATOR', score: 4, published: false, counted: false, created_at: '' },
      about_me: null,
    });
    const u = userEvent.setup();
    renderWithProviders(<RateJobCard jobId="job1" />);
    expect(await screen.findByText('Rate the operator')).toBeInTheDocument();
    expect(screen.getByText('Only Fikisha staff read comments.')).toBeInTheDocument();
    const send = screen.getByRole('button', { name: 'Send rating' });
    expect(send).toBeDisabled();
    await u.click(screen.getByRole('button', { name: '4 out of 5' }));
    await u.type(screen.getByLabelText('Comment (optional)'), 'Careful with the boxes.');
    await u.click(send);
    expect(submit).toHaveBeenCalledWith('job1', { score: 4, comment: 'Careful with the boxes.' });
    expect(await screen.findByText('You rated 4 out of 5.')).toBeInTheDocument();
  });

  it("shows the other side's score once published, never a comment", async () => {
    forJob.mockResolvedValue({
      can_rate: false,
      side: 'OPERATOR_RATES_BUSINESS',
      mine: null,
      about_me: { id: 'r2', side: 'BUSINESS_RATES_OPERATOR', score: 5, published: true, counted: true, created_at: '' },
    });
    renderWithProviders(<RateJobCard jobId="job1" />);
    expect(await screen.findByText('Their rating of you: 5 out of 5.')).toBeInTheDocument();
    expect(screen.getByText('The time to rate this job has passed.')).toBeInTheDocument();
  });

  it('staff see every rating with its comment', async () => {
    forJob.mockResolvedValue({
      can_rate: false,
      side: null,
      ratings: [
        { id: 'r1', side: 'BUSINESS_RATES_OPERATOR', score: 2, published: true, counted: false, created_at: '', comment: 'Late.' },
      ],
    });
    renderWithProviders(<RateJobCard jobId="job1" />);
    expect(await screen.findByText('Ratings')).toBeInTheDocument();
    expect(screen.getByText('Late.')).toBeInTheDocument();
    expect(screen.getByText(/Not counted/)).toBeInTheDocument();
  });

  it('stays hidden when the server refuses', async () => {
    forJob.mockRejectedValue(new Error('403'));
    const { container } = renderWithProviders(<RateJobCard jobId="job1" />);
    await new Promise((r) => setTimeout(r, 20));
    expect(container).toBeEmptyDOMElement();
  });
});
