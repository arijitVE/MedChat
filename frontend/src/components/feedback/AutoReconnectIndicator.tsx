import { useEffect, useState } from 'react';
import type { HTMLAttributes } from 'react';

interface AutoReconnectIndicatorProps extends HTMLAttributes<HTMLDivElement> {
  retryInSeconds?: number;
  onRetry?: () => void;
  active?: boolean;
}

export function AutoReconnectIndicator({
  retryInSeconds = 30,
  onRetry,
  active = true,
  className = '',
  ...props
}: AutoReconnectIndicatorProps) {
  const [remainingSeconds, setRemainingSeconds] = useState(retryInSeconds);

  useEffect(() => {
    setRemainingSeconds(retryInSeconds);
  }, [retryInSeconds]);

  useEffect(() => {
    if (!active) {
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      setRemainingSeconds((current) => {
        if (current <= 1) {
          onRetry?.();
          return retryInSeconds;
        }
        return current - 1;
      });
    }, 1000);

    return () => window.clearInterval(intervalId);
  }, [active, onRetry, retryInSeconds]);

  if (!active) {
    return null;
  }

  return (
    <div
      className={`text-xs text-clinical-text-muted ${className}`}
      role="status"
      aria-live="polite"
      {...props}
    >
      Retrying in {remainingSeconds}s...
    </div>
  );
}
