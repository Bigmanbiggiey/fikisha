import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { JobCard } from './JobCard';

describe('JobCard', () => {
  it('puts the reference and the state on the top row, before the route (Design Phase 7 F-01)', () => {
    render(
      <JobCard
        reference="346880"
        state="AT_PICKUP"
        stateLabel="Mahali pa kuchukua"
        route={{ from: 'Depot, Kitengela', to: 'Shop 4, Kitengela' }}
        cargo="20 cartons"
      />,
    );
    const ref = screen.getByText('346880');
    const chip = screen.getByText('Mahali pa kuchukua');
    // Same row: the chip's container is the reference's parent.
    expect(chip.closest('div')).toBe(ref.parentElement);
    expect(ref.compareDocumentPosition(screen.getByText(/Depot, Kitengela/)) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('includes the state in the accessible name of a clickable card', () => {
    render(
      <JobCard
        reference="346880"
        state="AT_PICKUP"
        stateLabel="At pickup"
        route={{ from: 'Depot', to: 'Shop 4' }}
        cargo="20 cartons"
        onClick={vi.fn()}
      />,
    );
    expect(screen.getByRole('button')).toHaveAccessibleName('Job 346880, At pickup, Depot to Shop 4');
  });
});
