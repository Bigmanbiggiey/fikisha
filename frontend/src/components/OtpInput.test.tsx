import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it } from 'vitest';

import { OtpInput } from './OtpInput';

function Harness({ error }: { error?: string }): JSX.Element {
  const [value, setValue] = useState('');
  return <OtpInput label="Pickup code" value={value} onChange={setValue} error={error} />;
}

describe('OtpInput', () => {
  it('exposes a single accessible group label, not six unlabelled cells', () => {
    render(<Harness />);
    expect(screen.getByRole('group', { name: 'Pickup code' })).toBeInTheDocument();
  });

  it('typing a digit advances focus to the next cell', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    const cells = screen.getAllByRole('textbox');
    cells[0]!.focus();
    await user.keyboard('1');
    expect(cells[1]).toHaveFocus();
  });

  it('pasting a full code distributes it across every cell', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    const cells = screen.getAllByRole('textbox');
    cells[0]!.focus();
    await user.paste('123456');
    expect(cells.map((c) => (c as HTMLInputElement).value)).toEqual(['1', '2', '3', '4', '5', '6']);
  });

  it('shows the error as an alert', () => {
    render(<Harness error="Wrong code — 2 attempts left" />);
    expect(screen.getByRole('alert')).toHaveTextContent('Wrong code — 2 attempts left');
  });
});
