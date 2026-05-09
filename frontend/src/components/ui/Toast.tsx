import type { HTMLAttributes, ReactNode } from 'react';

type ToastVariant = 'info' | 'success' | 'warning' | 'error';

interface ToastProps extends HTMLAttributes<HTMLDivElement> {
  variant?: ToastVariant;
  title?: string;
  children: ReactNode;
}

const variantClass: Record<ToastVariant, string> = {
  info: 'border-clinical-primary bg-clinical-primary-light text-clinical-primary-dark',
  success: 'border-clinical-auto bg-clinical-auto-bg text-clinical-auto',
  warning: 'border-clinical-warning bg-clinical-hitl-bg text-clinical-hitl',
  error: 'border-clinical-critical bg-clinical-critical-bg text-clinical-critical',
};

export function Toast({
  variant = 'info',
  title,
  children,
  className = '',
  ...props
}: ToastProps) {
  return (
    <div
      role={variant === 'error' ? 'alert' : 'status'}
      aria-live={variant === 'error' ? 'assertive' : 'polite'}
      className={`rounded-lg border px-4 py-3 text-sm shadow-sm ${variantClass[variant]} ${className}`}
      {...props}
    >
      {title ? <p className="font-medium">{title}</p> : null}
      <div className={title ? 'mt-1' : ''}>{children}</div>
    </div>
  );
}
