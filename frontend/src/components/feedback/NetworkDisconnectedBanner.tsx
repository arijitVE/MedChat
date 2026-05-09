import { useEffect, useState } from 'react';
import type { HTMLAttributes } from 'react';
import { WifiOff } from 'lucide-react';
import { useUIStore } from '../../store/uiStore';

export function NetworkDisconnectedBanner({
  className = '',
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  const setOffline = useUIStore((state) => state.setOffline);
  const [isOffline, setIsOffline] = useState(() => !navigator.onLine);

  useEffect(() => {
    setOffline(isOffline);
  }, [isOffline, setOffline]);

  useEffect(() => {
    const handleOffline = () => setIsOffline(true);
    const handleOnline = () => setIsOffline(false);

    window.addEventListener('offline', handleOffline);
    window.addEventListener('online', handleOnline);

    return () => {
      window.removeEventListener('offline', handleOffline);
      window.removeEventListener('online', handleOnline);
    };
  }, []);

  if (!isOffline) {
    return null;
  }

  return (
    <div
      role="status"
      aria-live="polite"
      className={`flex items-center justify-center gap-2 bg-clinical-offline-bg px-4 py-2 text-sm font-medium text-clinical-offline ${className}`}
      {...props}
    >
      <WifiOff className="h-4 w-4" aria-hidden="true" />
      <span>No internet connection - some features may be unavailable</span>
    </div>
  );
}
