import type { HTMLAttributes } from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from '../ui/Button';
import { AutoReconnectIndicator } from './AutoReconnectIndicator';

interface RetryPanelProps extends HTMLAttributes<HTMLDivElement> {
  onRetry: () => void;
  message?: string;
  retryInSeconds?: number;
}

export function RetryPanel({
  onRetry,
  message = 'Failed to load',
  retryInSeconds,
  className = '',
  ...props
}: RetryPanelProps) {
  return (
    <div
      role="alert"
      aria-live="assertive"
      className={`rounded-lg border border-clinical-border bg-clinical-surface px-6 py-8 text-center ${className}`}
      {...props}
    >
      <AlertCircle className="mx-auto h-6 w-6 text-clinical-warning" aria-hidden="true" />
      <p className="mt-3 text-sm font-medium text-clinical-text-primary">{message}</p>
      <div className="mt-4 flex items-center justify-center gap-3">
        <Button
          variant="secondary"
          onClick={onRetry}
          leftIcon={<RefreshCw className="h-4 w-4" aria-hidden="true" />}
        >
          Try Again
        </Button>
      </div>
      {retryInSeconds ? (
        <AutoReconnectIndicator
          className="mt-3"
          retryInSeconds={retryInSeconds}
          onRetry={onRetry}
        />
      ) : null}
    </div>
  );
}
