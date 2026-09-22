import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it } from 'vitest';

import { SignaturePad } from './SignaturePad';

// jsdom has no canvas 2D context without the native `canvas` package, so
// actual pointer-drawing can't be exercised here — that's covered by the
// live-browser verification pass. This test covers what's reachable:
// the accessible surface, and Clear resetting an already-captured value.
function Harness({ initial }: { initial: File | null }): JSX.Element {
  const [value, setValue] = useState<File | null>(initial);
  return <SignaturePad label="Recipient's signature" clearLabel="Clear" value={value} onChange={setValue} />;
}

describe('SignaturePad', () => {
  it('exposes the drawing surface with an accessible label', () => {
    render(<Harness initial={null} />);
    expect(screen.getByRole('img', { name: "Recipient's signature" })).toBeInTheDocument();
  });

  it('shows Clear once a signature exists, and it clears the value', async () => {
    const file = new File(['sig'], 'signature.png', { type: 'image/png' });
    const user = userEvent.setup();
    render(<Harness initial={file} />);

    const clearButton = screen.getByRole('button', { name: 'Clear' });
    await user.click(clearButton);
    expect(screen.queryByRole('button', { name: 'Clear' })).not.toBeInTheDocument();
  });
});
