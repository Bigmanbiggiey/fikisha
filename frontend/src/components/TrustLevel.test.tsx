import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { TrustLevel } from './TrustLevel';

describe('TrustLevel', () => {
  it('exposes the full meaning as the accessible name (not just "L2")', () => {
    render(
      <TrustLevel
        level={2}
        total={3}
        name="Established"
        bandDescription="cleared for deliveries up to KSh 250,000"
      />,
    );
    expect(
      screen.getByRole('img', {
        name: 'Level 2 of 3 — Established — cleared for deliveries up to KSh 250,000',
      }),
    ).toBeInTheDocument();
  });

  it('renders `total` pips, `level` of them filled', () => {
    const { container } = render(<TrustLevel level={1} total={3} name="Verified" />);
    const pips = container.querySelectorAll('span[aria-hidden] > span');
    expect(pips).toHaveLength(3);
    expect(pips[0]?.className).toContain('pip-filled');
    expect(pips[1]?.className).toContain('pip-empty');
  });

  it('is not a star rating — no radio/slider semantics', () => {
    render(<TrustLevel level={3} name="Trusted" />);
    expect(screen.queryByRole('slider')).not.toBeInTheDocument();
    expect(screen.queryByRole('radiogroup')).not.toBeInTheDocument();
  });
});
