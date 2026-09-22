import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { beforeAll, describe, expect, it, vi } from 'vitest';

import { PhotoCapture } from './PhotoCapture';

// jsdom doesn't implement the Blob URL APIs — stub them (real browsers do).
beforeAll(() => {
  URL.createObjectURL = vi.fn(() => 'blob:mock');
  URL.revokeObjectURL = vi.fn();
});

function Harness(): JSX.Element {
  const [file, setFile] = useState<File | null>(null);
  return (
    <PhotoCapture
      value={file}
      onChange={setFile}
      label="Take photo of the goods"
      retakeLabel="Retake"
      addedLabel="Photo added"
    />
  );
}

describe('PhotoCapture', () => {
  it('shows the camera button, then the thumbnail + status once a photo is captured, then lets the driver retake', async () => {
    const user = userEvent.setup();
    render(<Harness />);

    expect(screen.getByRole('button', { name: 'Take photo of the goods' })).toBeInTheDocument();

    const file = new File(['goods'], 'goods.jpg', { type: 'image/jpeg' });
    const input = screen.getByLabelText('Take photo of the goods', { selector: 'input' });
    await user.upload(input, file);

    expect(await screen.findByRole('status')).toHaveTextContent('Photo added');
    expect(screen.queryByRole('button', { name: 'Take photo of the goods' })).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Retake' }));
    expect(await screen.findByRole('button', { name: 'Take photo of the goods' })).toBeInTheDocument();
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });
});
