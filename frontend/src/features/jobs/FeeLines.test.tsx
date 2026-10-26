import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { renderWithProviders } from '@/test/renderWithProviders';

import { FeeLines } from './FeeLines';

describe('FeeLines (commission split, ADR-2D-55)', () => {
  it('shows the business its fee and what it pays in total', () => {
    renderWithProviders(
      <FeeLines
        fee={{ party: 'BUSINESS', rate: '0.0500', fee_kes: 12_500, total_cost_kes: 262_500 }}
      />,
    );
    expect(screen.getByText('Fikisha fee (5%)')).toBeInTheDocument();
    expect(screen.getByText('KSh 125')).toBeInTheDocument();
    expect(screen.getByText('You pay in total')).toBeInTheDocument();
    expect(screen.getByText('KSh 2,625')).toBeInTheDocument();
    expect(screen.getByText(/Pay the operator the agreed price/)).toBeInTheDocument();
  });

  it('shows the operator its fee and what it keeps', () => {
    renderWithProviders(
      <FeeLines
        fee={{ party: 'OPERATOR', rate: '0.0500', fee_kes: 12_500, operator_keeps_kes: 237_500 }}
        compact
      />,
    );
    expect(screen.getByText('You keep')).toBeInTheDocument();
    expect(screen.getByText('KSh 2,375')).toBeInTheDocument();
    expect(screen.queryByText(/weekly statement/)).not.toBeInTheDocument();
  });
});
