import { screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/services/problem';
import { renderWithProviders } from '@/test/renderWithProviders';

import { EmptyState } from './EmptyState';
import { ErrorState } from './ErrorState';

const problem = (status: number) =>
  new ApiError({ type: 'about:blank', title: 'x', status, code: 'x', detail: '' }, status, '');

describe('Increment 10f exception states', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('EmptyState says offline instead of "nothing here" when offline', () => {
    vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(false);
    renderWithProviders(<EmptyState title="No messages yet" />);
    expect(screen.getByText("You're offline")).toBeInTheDocument();
    expect(screen.queryByText('No messages yet')).not.toBeInTheDocument();
  });

  it('EmptyState is unchanged online', () => {
    renderWithProviders(<EmptyState title="No messages yet" />);
    expect(screen.getByText('No messages yet')).toBeInTheDocument();
  });

  it.each([403, 404, 410])('ErrorState offers Home, not "Try again", for a %s', (status) => {
    renderWithProviders(<ErrorState message="Nope" onRetry={() => {}} error={problem(status)} />);
    expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Go to Home' })).toHaveAttribute('href', '/home');
  });

  it('ErrorState keeps "Try again" for a network or server error', () => {
    renderWithProviders(<ErrorState message="Down" onRetry={() => {}} error={problem(503)} />);
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
  });
});
