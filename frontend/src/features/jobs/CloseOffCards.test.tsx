import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/renderWithProviders';

import { OperatorPaymentCard, SenderCloseOffCard } from './CloseOffCards';
import type { Job } from './types';

const closeJob = vi.fn();
vi.mock('./jobsApi', () => ({ jobsApi: { closeJob: (...a: unknown[]) => closeJob(...a) } }));
vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: () => Promise.reject(new Error('anon')), logout: vi.fn() },
}));

const job = (overrides: Partial<Job> = {}): Job =>
  ({ id: 'j1', status: 'DELIVERED', payment_record: null, ...overrides }) as Job;

describe('close-off (founder 2026-10-20, PD-3 / PD-4)', () => {
  beforeEach(() => closeJob.mockReset().mockResolvedValue({ id: 'j1', status: 'COMPLETED' }));

  it('the sender records how they paid and closes the job', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SenderCloseOffCard job={job()} />);
    expect(screen.getByText(/Fikisha doesn't take or move the money/)).toBeInTheDocument();
    await user.type(screen.getByLabelText(/M-Pesa code/), 'sgh7k2l9pq');
    await user.click(screen.getByRole('button', { name: 'Confirm and close the job' }));
    await waitFor(() =>
      expect(closeJob).toHaveBeenCalledWith(
        'j1',
        { payment_method: 'MPESA', mpesa_reference: 'SGH7K2L9PQ' },
        expect.any(String),
      ),
    );
  });

  it('cash needs no code', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SenderCloseOffCard job={job()} />);
    await user.click(screen.getByRole('radio', { name: /Cash/ }));
    expect(screen.queryByLabelText(/M-Pesa code/)).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Confirm and close the job' }));
    await waitFor(() =>
      expect(closeJob).toHaveBeenCalledWith('j1', { payment_method: 'CASH', mpesa_reference: undefined }, expect.any(String)),
    );
  });

  it('the operator waits for the sender and can say they were not paid', () => {
    renderWithProviders(<OperatorPaymentCard job={job()} />);
    expect(screen.getByText('Waiting for the sender')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: "I haven't been paid" })).toHaveAttribute(
      'href',
      '/jobs/j1/report-issue?type=NON_PAYMENT',
    );
  });

  it('the operator sees what the sender recorded once completed', () => {
    renderWithProviders(
      <OperatorPaymentCard
        job={job({
          status: 'COMPLETED',
          payment_record: { method: 'MPESA', mpesa_reference: 'SGH7K2L9PQ', recorded_at: '2026-10-20T10:00:00Z' },
        })}
      />,
    );
    expect(screen.getByText(/Paid by M-Pesa · M-Pesa code SGH7K2L9PQ/)).toBeInTheDocument();
  });
});
