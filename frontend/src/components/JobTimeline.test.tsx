import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { JobTimeline, type TimelineStep } from './JobTimeline';

const steps: TimelineStep[] = [
  { id: 'req', label: 'Requested', node: 'done', time: '13:02', actor: 'You' },
  {
    id: 'pick',
    label: 'Picked up',
    node: 'current',
    time: '14:24',
    proof: 'OTP',
    marker: { text: 'Verified pickup', tone: 'success' },
  },
  { id: 'transit', label: 'In transit', node: 'upcoming' },
  { id: 'sync', label: 'At destination', node: 'pending-sync' },
];

describe('JobTimeline', () => {
  it('renders an ordered list with aria-current on the current step', () => {
    render(<JobTimeline steps={steps} />);
    expect(screen.getByRole('list')).toBeInTheDocument();
    const current = screen.getByText('Picked up').closest('li');
    expect(current).toHaveAttribute('aria-current', 'step');
  });

  it('shows the proof chip and the verified/attested marker', () => {
    render(<JobTimeline steps={steps} />);
    expect(screen.getByText('OTP')).toBeInTheDocument();
    expect(screen.getByText('Verified pickup')).toBeInTheDocument();
  });

  it('marks a pending-sync step as "recorded on this phone · syncing"', () => {
    render(<JobTimeline steps={steps} />);
    expect(screen.getByText('recorded on this phone · syncing')).toBeInTheDocument();
  });

  it('renders the Under dispute overlay, keeping prior steps', () => {
    render(<JobTimeline steps={steps} endCap="disputed" />);
    expect(screen.getByText(/Under dispute/)).toBeInTheDocument();
    expect(screen.getByText('Requested')).toBeInTheDocument();
  });

  it('renders Cancelled and Failed as distinct end-caps', () => {
    const { rerender } = render(<JobTimeline steps={steps} endCap="cancelled" />);
    expect(screen.getByText('Cancelled')).toBeInTheDocument();
    rerender(<JobTimeline steps={steps} endCap="failed" />);
    expect(screen.getByText("Couldn't complete")).toBeInTheDocument();
  });
});
