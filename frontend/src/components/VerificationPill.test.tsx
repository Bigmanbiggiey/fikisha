import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { VerificationPill } from './VerificationPill';
import { VERIFICATION_GROUP_OF, type VerificationState } from '@/design/tokens';

describe('VerificationPill', () => {
  it('maps INFO_REQUESTED, REJECTED and effective EXPIRED to "Needs attention"', () => {
    (['INFO_REQUESTED', 'REJECTED', 'EXPIRED'] as VerificationState[]).forEach((s) => {
      expect(VERIFICATION_GROUP_OF[s]).toBe('needs_attention');
    });
    render(<VerificationPill domain="Driving licence" state="REJECTED" />);
    expect(screen.getByText('Driving licence · Needs attention')).toBeInTheDocument();
  });

  it('maps VERIFIED to "Verified" with a check shape', () => {
    const { container } = render(<VerificationPill domain="Identity" state="VERIFIED" />);
    expect(screen.getByText('Identity · Verified')).toBeInTheDocument();
    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  it('maps NOT_SUBMITTED to "Required"', () => {
    render(<VerificationPill domain="Good conduct" state="NOT_SUBMITTED" />);
    expect(screen.getByText('Good conduct · Required')).toBeInTheDocument();
  });

  it('never renders a bare "Verified operator" style badge (domain is always named)', () => {
    render(<VerificationPill domain="Vehicle" state="VERIFIED" />);
    expect(screen.queryByText('Verified')).not.toBeInTheDocument();
    expect(screen.getByText(/^Vehicle · /)).toBeInTheDocument();
  });
});
