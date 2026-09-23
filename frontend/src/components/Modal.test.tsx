import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { Modal } from './Modal';

function Harness({
  dismissible = true,
  onClose,
}: {
  dismissible?: boolean;
  onClose?: () => void;
}): JSX.Element {
  const [open, setOpen] = useState(true);
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>
        opener
      </button>
      <Modal
        open={open}
        onClose={() => {
          onClose?.();
          setOpen(false);
        }}
        title="Confirm pickup"
        dismissible={dismissible}
        footer={<button type="button">Confirm</button>}
      >
        <p>Body</p>
      </Modal>
    </>
  );
}

describe('Modal', () => {
  it('renders as a labelled modal dialog', () => {
    render(<Harness />);
    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveAccessibleName('Confirm pickup');
  });

  it('closes on Escape when dismissible', async () => {
    const onClose = vi.fn();
    render(<Harness onClose={onClose} />);
    await userEvent.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalled();
  });

  it('ignores Escape when not dismissible', async () => {
    const onClose = vi.fn();
    render(<Harness dismissible={false} onClose={onClose} />);
    await userEvent.keyboard('{Escape}');
    expect(onClose).not.toHaveBeenCalled();
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('has no Close control when not dismissible', () => {
    render(<Harness dismissible={false} />);
    expect(screen.queryByRole('button', { name: 'Close' })).not.toBeInTheDocument();
  });
  it('keeps focus in a field while typing (inline onClose re-created each render)', async () => {
    // Regression (Design Phase 6 Increment 8): the focus effect used to
    // re-run on every re-render, yanking focus to the Close button so the
    // next Space closed the modal mid-sentence.
    function Typing(): JSX.Element {
      const [open, setOpen] = useState(true);
      const [text, setText] = useState('');
      return (
        <Modal open={open} onClose={() => setOpen(false)} title="Tell us why">
          <label htmlFor="r">Reason</label>
          <textarea id="r" value={text} onChange={(e) => setText(e.target.value)} />
        </Modal>
      );
    }
    const user = userEvent.setup();
    render(<Typing />);
    const field = screen.getByLabelText('Reason');
    await user.click(field);
    await user.type(field, 'two words here');
    expect(field).toHaveValue('two words here');
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });
});
