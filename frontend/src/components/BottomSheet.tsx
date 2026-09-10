import type { ReactNode } from 'react';

import { Modal } from './Modal';

/**
 * BottomSheet — Design Phase 4 §30.19. A Modal locked to the sheet presentation
 * at every width (used for quick contextual actions on mobile).
 */
export function BottomSheet({
  open,
  onClose,
  title,
  children,
  footer,
  dismissible = true,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
  dismissible?: boolean;
}): JSX.Element | null {
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={title}
      footer={footer}
      dismissible={dismissible}
      variant="sheet"
    >
      {children}
    </Modal>
  );
}
