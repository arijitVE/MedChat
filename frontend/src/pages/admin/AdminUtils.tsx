import type { ReactNode } from 'react';
import { RetryPanel } from '../../components/feedback/RetryPanel';
import { Card } from '../../components/ui/Card';
import { EmptyState } from '../../components/ui/EmptyState';
import { Skeleton } from '../../components/ui/Skeleton';
import { normalizeApiError } from '../../lib/apiError';

export function PageHeader({ title, description }: { title: string; description: string }) {
  return (
    <div>
      <h1 className="text-lg font-semibold text-clinical-text-primary">{title}</h1>
      <p className="mt-1 text-sm text-clinical-text-secondary">{description}</p>
    </div>
  );
}

export function StatGrid({ stats }: { stats: Array<{ label: string; value: number | string }> }) {
  return (
    <div className="grid gap-4 md:grid-cols-4">
      {stats.map((stat) => (
        <Card key={stat.label}>
          <p className="text-sm text-clinical-text-secondary">{stat.label}</p>
          <p className="mt-2 text-2xl font-semibold text-clinical-text-primary">{stat.value}</p>
        </Card>
      ))}
    </div>
  );
}

export function QueryState({
  isLoading,
  isError,
  error,
  onRetry,
  isEmpty,
  emptyTitle,
  children,
}: {
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  onRetry: () => void;
  isEmpty: boolean;
  emptyTitle: string;
  children: ReactNode;
}) {
  if (isError) {
    return <RetryPanel onRetry={onRetry} message={normalizeApiError(error).message} />;
  }

  if (isLoading) {
    return <Skeleton variant="table-row" rows={8} />;
  }

  if (isEmpty) {
    return <EmptyState title={emptyTitle} />;
  }

  return <>{children}</>;
}
