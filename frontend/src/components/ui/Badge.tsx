import type { HTMLAttributes, ReactNode } from 'react';

type BadgeVariant = 'auto' | 'hitl' | 'verified' | 'final' | 'processing';

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  children: ReactNode;
}

const variantClass: Record<BadgeVariant, string> = {
  auto: 'bg-clinical-auto-bg text-clinical-auto',
  hitl: 'bg-clinical-hitl-bg text-clinical-hitl',
  verified: 'bg-clinical-verified-bg text-clinical-verified',
  final: 'bg-clinical-final-bg text-clinical-final',
  processing: 'bg-slate-100 text-clinical-text-secondary',
};

export function Badge({
  variant = 'processing',
  children,
  className = '',
  ...props
}: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${variantClass[variant]} ${className}`}
      {...props}
    >
      {children}
    </span>
  );
}
