import type { HTMLAttributes, ReactNode } from 'react';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

export function Card({ children, className = '', ...props }: CardProps) {
  return (
    <div
      className={`rounded-lg border border-clinical-border bg-clinical-surface p-6 shadow-sm ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ children, className = '', ...props }: CardProps) {
  return (
    <div className={`mb-4 flex items-start justify-between gap-4 ${className}`} {...props}>
      {children}
    </div>
  );
}

export function CardTitle({
  children,
  className = '',
  ...props
}: HTMLAttributes<HTMLHeadingElement> & { children: ReactNode }) {
  return (
    <h2 className={`text-base font-semibold text-clinical-text-primary ${className}`} {...props}>
      {children}
    </h2>
  );
}

export function CardContent({ children, className = '', ...props }: CardProps) {
  return (
    <div className={className} {...props}>
      {children}
    </div>
  );
}
