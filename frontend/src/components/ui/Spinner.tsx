import type { HTMLAttributes } from 'react';

type SpinnerSize = 'sm' | 'md' | 'lg';

interface SpinnerProps extends HTMLAttributes<HTMLDivElement> {
  size?: SpinnerSize;
  label?: string;
}

const sizeClass: Record<SpinnerSize, string> = {
  sm: 'h-4 w-4 border-2',
  md: 'h-5 w-5 border-2',
  lg: 'h-8 w-8 border-4',
};

export function Spinner({
  size = 'md',
  label = 'Loading',
  className = '',
  ...props
}: SpinnerProps) {
  return (
    <div
      className={`inline-flex items-center justify-center ${className}`}
      role="status"
      aria-live="polite"
      {...props}
    >
      <span
        className={`${sizeClass[size]} animate-spin rounded-full border-current border-t-transparent text-clinical-primary`}
        aria-hidden="true"
      />
      <span className="sr-only">{label}</span>
    </div>
  );
}
