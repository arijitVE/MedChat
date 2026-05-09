import { forwardRef } from 'react';
import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { Spinner } from './Spinner';

type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  loading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
}

const variantClass: Record<ButtonVariant, string> = {
  primary:
    'border border-clinical-primary bg-clinical-primary text-white hover:bg-clinical-primary-dark focus-visible:ring-clinical-primary',
  secondary:
    'border border-clinical-border bg-clinical-surface text-clinical-text-primary hover:bg-slate-50 focus-visible:ring-clinical-primary',
  danger:
    'border border-clinical-critical bg-clinical-critical text-white hover:bg-red-700 focus-visible:ring-clinical-critical',
  ghost:
    'border border-transparent bg-transparent text-clinical-text-secondary hover:bg-slate-100 hover:text-clinical-text-primary focus-visible:ring-clinical-primary',
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      loading = false,
      disabled = false,
      leftIcon,
      rightIcon,
      children,
      className = '',
      type = 'button',
      ...props
    },
    ref,
  ) => {
    const isDisabled = disabled || loading;

    return (
      <button
        ref={ref}
        type={type}
        disabled={isDisabled}
        className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60 ${variantClass[variant]} ${className}`}
        aria-busy={loading || undefined}
        {...props}
      >
        {loading ? <Spinner size="sm" label="Action in progress" /> : leftIcon}
        <span>{children}</span>
        {!loading ? rightIcon : null}
      </button>
    );
  },
);

Button.displayName = 'Button';
