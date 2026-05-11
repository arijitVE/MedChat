import { useEffect, useRef } from 'react';
import { AlertTriangle } from 'lucide-react';
import { Button } from '../ui/Button';

interface DuplicateWarningModalProps {
  type: 'exact' | 'probable';
  existingReportId: string;
  existingUploadedAt: string;
  uploadedByRole: 'doctor' | 'patient';
  onUseExisting: () => void;
  onForceUpload: () => void;
  useExistingLabel?: string;
  forceUploadLabel?: string;
  disclaimer?: string;
  onDismiss?: () => void;
  className?: string;
}

const focusableSelector = [
  'button:not([disabled])',
  'a[href]',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

export function DuplicateWarningModal({
  type,
  existingReportId,
  existingUploadedAt,
  uploadedByRole,
  onUseExisting,
  onForceUpload,
  useExistingLabel = 'Use existing',
  forceUploadLabel,
  disclaimer,
  onDismiss,
  className = '',
}: DuplicateWarningModalProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const canDismiss = type === 'probable' && Boolean(onDismiss);
  const title = type === 'exact' ? 'Exact duplicate found' : 'Probable duplicate found';

  useEffect(() => {
    const panel = panelRef.current;
    panel?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && canDismiss) {
        event.preventDefault();
        onDismiss?.();
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
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [canDismiss, onDismiss]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="duplicate-warning-title"
        tabIndex={-1}
        className={`w-full max-w-lg rounded-xl border bg-clinical-surface p-6 shadow-xl focus:outline-none ${
          type === 'exact' ? 'border-clinical-critical' : 'border-clinical-warning'
        } ${className}`}
      >
        <div className="flex items-start gap-3">
          <AlertTriangle
            className={type === 'exact' ? 'h-6 w-6 text-clinical-critical' : 'h-6 w-6 text-clinical-warning'}
            aria-hidden="true"
          />
          <div className="min-w-0 flex-1">
            <div className="flex items-start justify-between gap-3">
              <h2 id="duplicate-warning-title" className="text-base font-semibold text-clinical-text-primary">
                {title}
              </h2>
              {canDismiss ? (
                <button
                  type="button"
                  className="rounded-md px-2 py-1 text-clinical-text-muted hover:bg-slate-100 hover:text-clinical-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-clinical-primary"
                  onClick={onDismiss}
                  aria-label="Dismiss duplicate warning"
                >
                  X
                </button>
              ) : null}
            </div>
            <p className="mt-2 text-sm text-clinical-text-secondary">
              A {uploadedByRole} uploaded a similar report on{' '}
              {new Date(existingUploadedAt).toLocaleString()}.
            </p>
            <p className="mt-2 break-all text-xs text-clinical-text-muted">
              Existing report: {existingReportId}
            </p>
            {disclaimer ? (
              <p className="mt-3 rounded-md border border-clinical-warning bg-clinical-hitl-bg px-3 py-2 text-sm text-clinical-hitl">
                {disclaimer}
              </p>
            ) : null}
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-3">
          <Button variant="secondary" onClick={onUseExisting}>
            {useExistingLabel}
          </Button>
          <Button variant={type === 'exact' ? 'danger' : 'primary'} onClick={onForceUpload}>
            {forceUploadLabel ?? (type === 'exact' ? 'Force upload' : 'Force upload')}
          </Button>
        </div>
      </div>
    </div>
  );
}
