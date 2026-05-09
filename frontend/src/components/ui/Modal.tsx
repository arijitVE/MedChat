import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';

interface ModalProps {
  isOpen: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
  className?: string;
}

const focusableSelector = [
  'a[href]',
  'button:not([disabled])',
  'textarea:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

export function Modal({
  isOpen,
  title,
  children,
  onClose,
  className = '',
}: ModalProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const previousActiveElementRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    previousActiveElementRef.current = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;

    const panel = panelRef.current;
    const focusable = panel?.querySelectorAll<HTMLElement>(focusableSelector);
    const firstFocusable = focusable?.[0] ?? panel;
    firstFocusable?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
        return;
      }

      if (event.key !== 'Tab' || !panel) {
        return;
      }

      const elements = Array.from(panel.querySelectorAll<HTMLElement>(focusableSelector));
      if (elements.length === 0) {
        event.preventDefault();
        panel.focus();
        return;
      }

      const first = elements[0];
      const last = elements[elements.length - 1];

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      previousActiveElementRef.current?.focus();
    };
  }, [isOpen, onClose]);

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
      <button
        type="button"
        className="absolute inset-0 cursor-default"
        aria-label="Close modal"
        onClick={onClose}
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        tabIndex={-1}
        className={`relative w-full max-w-lg rounded-xl bg-clinical-surface p-6 shadow-xl focus:outline-none ${className}`}
      >
        <div className="mb-4 flex items-start justify-between gap-4">
          <h2 id="modal-title" className="text-base font-semibold text-clinical-text-primary">
            {title}
          </h2>
          <button
            type="button"
            className="rounded-md px-2 py-1 text-clinical-text-muted hover:bg-slate-100 hover:text-clinical-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-clinical-primary"
            onClick={onClose}
            aria-label="Close modal"
          >
            X
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
