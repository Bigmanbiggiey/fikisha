import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { NegotiationThread } from './NegotiationThread';
import type { NegotiationEntry } from '@/features/negotiation/types';

const entries: NegotiationEntry[] = [
  {
    id: 'e1',
    actor_role: 'BUSINESS',
    type: 'PROPOSE',
    amount_kes: 750_000,
    note: '',
    in_response_to_id: null,
    created_at: '2026-09-15T13:10:00Z',
    expires_at: null,
    effective_status: 'SUPERSEDED',
  },
  {
    id: 'e2',
    actor_role: 'OPERATOR',
    type: 'COUNTER',
    amount_kes: 780_000,
    note: 'Fuel is high today.',
    in_response_to_id: 'e1',
    created_at: '2026-09-15T13:14:00Z',
    expires_at: null,
    effective_status: 'ACTIVE',
  },
];

const labels = {
  youLabel: 'You',
  adminLabel: 'Platform Admin',
  operatorFallbackLabel: 'Operator',
  statusLabelFor: (key: string) => ({ current: 'Current', countered: 'Countered' })[key] ?? key,
  timeFor: () => '13:14',
};

describe('NegotiationThread', () => {
  it('renders entries in order, labeling "You" vs. the named counterparty', () => {
    render(
      <NegotiationThread entries={entries} viewerRole="BUSINESS" operatorDisplayName="Athi Movers" {...labels} />,
    );
    const items = screen.getAllByRole('listitem');
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent('You');
    expect(items[0]).toHaveTextContent('Countered');
    expect(items[1]).toHaveTextContent('Athi Movers');
    expect(items[1]).toHaveTextContent('Current');
    expect(items[1]).toHaveTextContent('Fuel is high today.');
  });

  it('falls back to a generic label when the operator name is unavailable', () => {
    render(
      <NegotiationThread entries={entries} viewerRole="BUSINESS" operatorDisplayName={null} {...labels} />,
    );
    expect(screen.getAllByText('Operator')).toHaveLength(1);
  });
});
