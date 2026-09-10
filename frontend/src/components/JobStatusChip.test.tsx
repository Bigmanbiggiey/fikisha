import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { JobStatusChip } from './JobStatusChip';
import { JOB_STATE_VISUAL, type JobState } from '@/design/tokens';

const ALL = Object.keys(JOB_STATE_VISUAL) as JobState[];

describe('JobStatusChip', () => {
  it('covers all 14 authoritative Job states', () => {
    expect(ALL).toHaveLength(14);
  });

  it.each(ALL)('renders %s with its approved label and a shape (icon)', (state) => {
    const { container } = render(<JobStatusChip state={state} />);
    expect(screen.getByText(JOB_STATE_VISUAL[state].labelEn)).toBeInTheDocument();
    // status is never colour-only: an icon accompanies the label
    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  it('renders CANCELLED distinct from COMPLETED (neutral vs success)', () => {
    const { container: cancelled } = render(<JobStatusChip state="CANCELLED" />);
    const { container: completed } = render(<JobStatusChip state="COMPLETED" />);
    expect(cancelled.firstElementChild?.className).toContain('neutral');
    expect(cancelled.firstElementChild?.className).not.toContain('success');
    expect(completed.firstElementChild?.className).toContain('success');
  });

  it('DISPUTED uses a solid strong treatment', () => {
    const { container } = render(<JobStatusChip state="DISPUTED" />);
    expect(container.firstElementChild?.className).toContain('warning-solid');
  });

  it('accepts a localized label override', () => {
    render(<JobStatusChip state="IN_TRANSIT" label="Njiani" />);
    expect(screen.getByText('Njiani')).toBeInTheDocument();
  });
});
