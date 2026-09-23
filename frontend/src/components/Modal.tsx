import { useCallback, useEffect, useId, useRef, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

import { Icon } from '@/design/Icon';
import { cn } from './cn';

const FOCUSABLE =
  'a[href],button:not([disabled]),textarea:not([disabled]),input:not([disabled]),select:not([disabled]),[tabindex]:not([tabindex="-1"])';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  /** footer actions (e.g. confirm / cancel) */
  footer?: ReactNode;
  /** Escape + scrim click close. Set false for a mandatory decision. */
  dismissible?: boolean;
  /** On < md this renders as a bottom sheet; on >= md as a centred dialog. */
  variant?: 'auto' | 'sheet' | 'center';
}

/**
 * Modal / dialog — Design Phase 4 §19/§30.18-19. No dependency: a minimal focus
 * trap, scrim, Escape-to-close, and focus restore. Bottom sheet on small
 * screens, centred dialog on larger ones (`variant="auto"`).
 */
export function Modal({
  open,
  onClose,
  title,
  children,
  footer,
  dismissible = true,
  variant = 'auto',
}: ModalProps): JSX.Element | null {
  const ref = useRef<HTMLDivElement>(null);
  const restoreRef = useRef<HTMLElement | null>(null);
  const titleId = useId();

  // The latest `onClose`/`dismissible`, read through a ref so the focus
  // effect below runs only when `open` changes. Callers pass an inline
  // `onClose` arrow, so depending on it re-ran the effect on every
  // re-render — i.e. every keystroke in a field inside the modal — which
  // yanked focus back to the first focusable element (the Close button),
  // where the next Space "clicked" Close. Found in Design Phase 6
  // Increment 8; it also affected Increment 4's counter-offer sheet.
  const closeRef = useRef<() => void>(() => undefined);
  closeRef.current = () => {
    if (dismissible) onClose();
  };
  const close = useCallback(() => closeRef.current(), []);

  useEffect(() => {
    if (!open) return;
    restoreRef.current = document.activeElement as HTMLElement | null;
    const node = ref.current;
    const first = node?.querySelector<HTMLElement>(FOCUSABLE);
    (first ?? node)?.focus();

    const onKey = (e: KeyboardEvent): void => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        close();
        return;
      }
      if (e.key !== 'Tab' || !node) return;
      const items = Array.from(node.querySelectorAll<HTMLElement>(FOCUSABLE));
      const firstEl = items[0];
      const lastEl = items[items.length - 1];
      if (!firstEl || !lastEl) {
        e.preventDefault();
        return;
      }
      if (e.shiftKey && document.activeElement === firstEl) {
        e.preventDefault();
        lastEl.focus();
      } else if (!e.shiftKey && document.activeElement === lastEl) {
        e.preventDefault();
        firstEl.focus();
      }
    };
    document.addEventListener('keydown', onKey, true);
    const { overflow } = document.body.style;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey, true);
      document.body.style.overflow = overflow;
      restoreRef.current?.focus?.();
    };
  }, [open, close]);

  if (!open) return null;

  const shell =
    variant === 'sheet'
      ? 'items-end'
      : variant === 'center'
        ? 'items-center'
        : 'items-end md:items-center';
  const panel =
    variant === 'sheet'
      ? 'rounded-t-lg'
      : variant === 'center'
        ? 'rounded-lg'
        : 'rounded-t-lg md:rounded-lg';

  return createPortal(
    <div
      className={cn('fixed inset-0 z-modal flex justify-center bg-surface-overlay p-0 md:p-4', shell)}
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) close();
      }}
    >
      <div
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className={cn(
          'w-full max-w-md bg-surface-raised shadow-e3 outline-none',
          panel,
        )}
      >
        <div className="flex items-start justify-between gap-3 border-b border-line px-4 py-3">
          <h2 id={titleId} className="text-h2 text-fg">
            {title}
          </h2>
          {dismissible && (
            <button
              type="button"
              onClick={onClose}
              aria-label="Close"
              className="min-h-target min-w-target -mr-2 -mt-2 inline-flex items-center justify-center text-fg-secondary"
            >
              <Icon name="close" size={20} />
            </button>
          )}
        </div>
        <div className="px-4 py-4 text-body text-fg">{children}</div>
        {footer && (
          <div className="flex flex-wrap justify-end gap-2 border-t border-line px-4 py-3">
            {footer}
          </div>
        )}
      </div>
    </div>,
    document.body,
  );
}
