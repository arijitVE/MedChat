import type { HTMLAttributes, ReactNode } from 'react';

interface EmptyStateProps extends HTMLAttributes<HTMLDivElement> {
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({
  title,
  description,
  action,
  className = '',
  ...props
}: EmptyStateProps) {
  return (
    <div
      className={`rounded-lg border border-dashed border-clinical-border bg-clinical-surface px-6 py-10 text-center ${className}`}
      {...props}
    >
      <h3 className="text-sm font-semibold text-clinical-text-primary">{title}</h3>
      {description ? (
        <p className="mx-auto mt-2 max-w-md text-sm text-clinical-text-secondary">
          {description}
        </p>
      ) : null}
      {action ? <div className="mt-4 flex justify-center">{action}</div> : null}
    </div>
  );
}
