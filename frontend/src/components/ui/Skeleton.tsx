import type { HTMLAttributes } from 'react';

type SkeletonVariant = 'text' | 'card' | 'table-row' | 'stat' | 'chart' | 'file' | 'field-row';

interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  variant?: SkeletonVariant;
  rows?: number;
}

const variantClass: Record<SkeletonVariant, string> = {
  text: 'h-4 w-full',
  card: 'h-24 w-full',
  'table-row': 'h-10 w-full',
  stat: 'h-16 w-full',
  chart: 'h-48 w-full',
  file: 'h-full min-h-80 w-full bg-slate-100',
  'field-row': 'h-8 w-full',
};

export function Skeleton({
  variant = 'text',
  rows = 1,
  className = '',
  ...props
}: SkeletonProps) {
  if (rows > 1) {
    return (
      <div className={`space-y-2 ${className}`} role="status" aria-live="polite" {...props}>
        {Array.from({ length: rows }, (_, index) => (
          <div
            key={index}
            className={`${variantClass[variant]} animate-pulse rounded bg-slate-200`}
          />
        ))}
        <span className="sr-only">Loading</span>
      </div>
    );
  }

  return (
    <div
      className={`${variantClass[variant]} animate-pulse rounded bg-slate-200 ${className}`}
      role="status"
      aria-live="polite"
      {...props}
    >
      <span className="sr-only">Loading</span>
    </div>
  );
}
