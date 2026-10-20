import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/renderWithProviders';

import { BusinessRecordCard } from './BusinessRecordCard';

const businessRecord = vi.fn();

vi.mock('./adminApi', () => ({
  adminApi: { businessRecord: (...a: unknown[]) => businessRecord(...a) },
}));

beforeEach(() => businessRecord.mockReset());

describe('staff business record (trust plan A8)', () => {
  it('keeps open reports, closures, findings and unfounded reports apart', async () => {
    businessRecord.mockResolvedValue({
      open_reports: [{ id: 'i1', job_id: 'j1', type: 'NON_PAYMENT', reporter_party: 'OPERATOR', created_at: '2026-10-20T08:00:00Z' }],
      closed_incidents: [{ id: 'i2', job_id: 'j2', type: 'DELAY', reason_code: 'PAYMENT_MADE', closed_at: '2026-10-20T09:00:00Z' }],
      findings_against: [
        { id: 'f1', incident_id: 'i2', type: 'DELAY', reason: 'Kept the driver waiting.', current: false, created_at: '' },
      ],
      unfounded_reports: [],
      rating: { average: null, count: 1 },
      cancellation_flags: [{ id: 'c1', status: 'CLEARED', count: 3, created_at: '2026-10-19T08:00:00Z' }],
    });
    renderWithProviders(<BusinessRecordCard businessId="b1" />);
    expect(await screen.findByText('Track record')).toBeInTheDocument();
    expect(screen.getByText('Rating from operators: not enough ratings yet (1 counted)')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Not paid' })).toHaveAttribute('href', '/incidents/i1');
    expect(screen.getByText(/Payment made/)).toBeInTheDocument();
    expect(screen.getByText(/Kept the driver waiting. \(replaced\)/)).toBeInTheDocument();
    expect(screen.getByText(/3 late cancellations or wasted trips · cleared/)).toBeInTheDocument();
  });
});
