import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { JobStatusHeader } from '@/components/JobStatusHeader';
import { Select } from '@/components/Select';
import { Textarea } from '@/components/Textarea';
import { StaffJobContext } from '@/features/ops/StaffJobContext';
import { renderWithProviders } from '@/test/renderWithProviders';

import { businessNextAction, needsBusinessAttention } from './jobHelpers';
import type { Job } from './types';

const monitor = vi.fn();
const highValueQueue = vi.fn();

vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: () => Promise.reject(new Error('anon')), logout: vi.fn() },
}));
vi.mock('@/features/ops/opsApi', () => ({
  opsApi: {
    monitor: (...a: unknown[]) => monitor(...a),
    highValueQueue: (...a: unknown[]) => highValueQueue(...a),
  },
}));

const page = (data: unknown[]) => ({ data, page: { next_cursor: null, prev_cursor: null } });

describe('P-08 job header', () => {
  it('is the page h1: the reference, then the route', () => {
    renderWithProviders(
      <JobStatusHeader
        reference="7F3A2C"
        state="IN_TRANSIT"
        stateLabel="In transit"
        route={{ from: 'Depot', to: 'Shop 4' }}
        line="On the way."
      />,
    );
    expect(screen.getByRole('heading', { level: 1, name: 'Job 7F3A2C' })).toBeInTheDocument();
    expect(screen.getByText('Depot → Shop 4')).toBeInTheDocument();
  });

  it('shows staff the business, the band and a pending high-value review', async () => {
    const job = { id: '01a1-7f3a2c', status: 'CONFIRMED', value_band: 'HIGH', is_high_value: true } as unknown as Job;
    monitor.mockResolvedValue(page([{ id: job.id, business_name: 'Kitengela Traders' }]));
    highValueQueue.mockResolvedValue(page([{ id: job.id }]));
    renderWithProviders(<StaffJobContext job={job} />);
    expect(await screen.findByText('Kitengela Traders')).toBeInTheDocument();
    expect(await screen.findByText('High-value review pending')).toBeInTheDocument();
    expect(monitor).toHaveBeenCalledWith({ ref: '7F3A2C' });
  });
});

describe('P-09 delivered completes on its own', () => {
  it('is not an action and not under "Needs your action"', () => {
    expect(businessNextAction('DELIVERED')).toBeNull();
    expect(needsBusinessAttention('DELIVERED')).toBe(false);
    expect(needsBusinessAttention('AT_PICKUP')).toBe(true);
  });
});

describe('P-13 form controls', () => {
  beforeEach(() => {
    monitor.mockReset();
  });

  it('Textarea and Select mark themselves invalid and keep their names', () => {
    renderWithProviders(
      <>
        <label htmlFor="r">Reason</label>
        <Textarea id="r" invalid />
        <Select aria-label="Role" inline defaultValue="b">
          <option value="a">A</option>
          <option value="b">B</option>
        </Select>
      </>,
    );
    expect(screen.getByLabelText('Reason')).toHaveAttribute('aria-invalid', 'true');
    const select = screen.getByRole('combobox', { name: 'Role' });
    expect(select).toHaveValue('b');
    expect(select).not.toHaveAttribute('aria-invalid');
    expect(select.className).toContain('min-h-target');
  });
});
