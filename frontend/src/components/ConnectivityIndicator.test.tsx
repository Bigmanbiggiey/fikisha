import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ConnectivityIndicator } from './ConnectivityIndicator';

describe('ConnectivityIndicator', () => {
  it('is a polite live status region', () => {
    render(<ConnectivityIndicator state="online" />);
    const el = screen.getByRole('status');
    expect(el).toHaveAttribute('aria-live', 'polite');
  });

  it('shows a word (not colour-only) for each state', () => {
    const { rerender } = render(<ConnectivityIndicator state="online" />);
    expect(screen.getByText('Synced')).toBeInTheDocument();
    rerender(<ConnectivityIndicator state="offline" />);
    expect(screen.getByText('Offline')).toBeInTheDocument();
    rerender(<ConnectivityIndicator state="syncing" />);
    expect(screen.getByText('Syncing…')).toBeInTheDocument();
  });

  it('shows the count for the sync-issue state', () => {
    render(<ConnectivityIndicator state="sync_issue" count={3} />);
    expect(screen.getByText('Sync issues (3)')).toBeInTheDocument();
  });
});
