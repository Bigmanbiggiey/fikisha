import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it } from 'vitest';

import { EligibilityRow } from './EligibilityRow';

function Harness({
  eligible,
  reasons,
}: {
  eligible: boolean;
  reasons?: string[];
}): JSX.Element {
  const [selected, setSelected] = useState<string | null>(null);
  return (
    <EligibilityRow
      name="driver"
      value="d1"
      label="D. Kamau"
      meta="Level 1"
      eligible={eligible}
      reasons={reasons}
      selected={selected === 'd1'}
      onSelect={setSelected}
    />
  );
}

describe('EligibilityRow', () => {
  it('an eligible row is selectable and carries no reason text', async () => {
    const user = userEvent.setup();
    render(<Harness eligible={true} />);
    const radio = screen.getByRole('radio', { name: 'D. Kamau' });
    expect(radio).not.toBeDisabled();
    await user.click(radio);
    expect(radio).toBeChecked();
  });

  it('an ineligible row is disabled, shows the reason, and folds it into the accessible name', () => {
    render(<Harness eligible={false} reasons={['Level 1 — needs Level 2 for Elevated.']} />);
    const radio = screen.getByRole('radio', { name: /D\. Kamau — Level 1 — needs Level 2/ });
    expect(radio).toBeDisabled();
    expect(radio.closest('label')).toHaveAttribute('aria-disabled', 'true');
    expect(screen.getByText('Level 1 — needs Level 2 for Elevated.')).toBeInTheDocument();
  });
});
