import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/renderWithProviders';

import { FindingPanel } from './FindingPanel';
import type { Incident } from './types';

const recordFinding = vi.fn();
const markUnfounded = vi.fn();

vi.mock('./incidentsApi', () => ({
  incidentsApi: {
    recordFinding: (...a: unknown[]) => recordFinding(...a),
    markUnfounded: (...a: unknown[]) => markUnfounded(...a),
  },
}));

function incident(overrides: Partial<Incident> = {}): Incident {
  return {
    id: 'inc1',
    job_id: 'job1',
    type: 'DAMAGE',
    other_label: '',
    severity: '',
    status: 'OPEN',
    description: '',
    reported_by_kind: 'USER',
    created_at: '2026-10-20T08:00:00Z',
    sla_ack_due_at: null,
    sla_action_due_at: null,
    sla_resolution_due_at: null,
    evidence: [],
    statements: [],
    closure: null,
    finding: null,
    ...overrides,
  };
}

const REASON = 'Photos show the box crushed at pickup.';

beforeEach(() => {
  recordFinding.mockReset().mockResolvedValue(incident());
  markUnfounded.mockReset().mockResolvedValue(incident());
});

describe('Fikisha finding panel (trust plan A2, A3)', () => {
  it('a party sees nothing until a finding exists, then the outcome without the reason', () => {
    const { unmount } = renderWithProviders(
      <FindingPanel incident={incident()} isStaff={false} isPlatformAdmin={false} onChanged={vi.fn()} />,
    );
    expect(screen.queryByText("Fikisha's finding")).not.toBeInTheDocument();
    unmount();
    renderWithProviders(
      <FindingPanel
        incident={incident({
          finding: { id: 'f1', outcome: 'AT_FAULT', parties: ['DRIVER'], created_at: '2026-10-20T09:00:00Z' },
        })}
        isStaff={false}
        isPlatformAdmin={false}
        onChanged={vi.fn()}
      />,
    );
    expect(screen.getByText('Found at fault: Driver')).toBeInTheDocument();
    expect(screen.getByText(/not a legal ruling/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Save finding' })).not.toBeInTheDocument();
  });

  it('staff record an at-fault finding naming the parties offered by the job', async () => {
    const u = userEvent.setup();
    renderWithProviders(
      <FindingPanel
        incident={incident({ finding_candidates: ['BUSINESS', 'DRIVER', 'GROUP'], finding_history: [] })}
        isStaff
        isPlatformAdmin={false}
        onChanged={vi.fn()}
      />,
    );
    await u.selectOptions(screen.getByLabelText('Finding'), 'AT_FAULT');
    expect(screen.getByText(/Naming the group doesn't name the driver/)).toBeInTheDocument();
    await u.type(screen.getByLabelText('Reason (at least 10 characters)'), REASON);
    const save = screen.getByRole('button', { name: 'Save finding' });
    expect(save).toBeDisabled(); // nobody named yet
    await u.click(screen.getByLabelText('Group'));
    await u.click(save);
    expect(recordFinding).toHaveBeenCalledWith('inc1', {
      outcome: 'AT_FAULT',
      parties: ['GROUP'],
      reason: REASON,
    });
  });

  it('a Platform Admin can mark a closed no-fault report unfounded', async () => {
    const u = userEvent.setup();
    renderWithProviders(
      <FindingPanel
        incident={incident({
          status: 'RESOLVED',
          finding: { id: 'f1', outcome: 'NO_FAULT', parties: [], created_at: '2026-10-20T09:00:00Z' },
          finding_history: [],
          finding_candidates: ['BUSINESS', 'DRIVER'],
          unfounded: null,
        })}
        isStaff
        isPlatformAdmin
        onChanged={vi.fn()}
      />,
    );
    await u.type(screen.getByLabelText('Why the report was unfounded'), 'Goods were checked on arrival.');
    await u.click(screen.getByRole('button', { name: 'Mark report unfounded' }));
    expect(markUnfounded).toHaveBeenCalledWith('inc1', 'Goods were checked on arrival.');
  });

  it('an undetermined finding offers no unfounded action', () => {
    renderWithProviders(
      <FindingPanel
        incident={incident({
          status: 'RESOLVED',
          finding: { id: 'f1', outcome: 'UNDETERMINED', parties: [], created_at: '2026-10-20T09:00:00Z' },
          finding_history: [],
          finding_candidates: ['BUSINESS', 'DRIVER'],
          unfounded: null,
        })}
        isStaff
        isPlatformAdmin
        onChanged={vi.fn()}
      />,
    );
    expect(screen.getByText("Couldn't be determined", { selector: 'p' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Mark report unfounded' })).not.toBeInTheDocument();
  });
});
