import { useEffect, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText } from 'lucide-react';
import { useMarkNotificationRead, useNotifications } from '../../hooks/useNotifications';
import type { NotificationItem } from '../../types/notification';
import type { User } from '../../types/auth';

interface NotificationPanelProps {
  isOpen: boolean;
  role: Exclude<User['role'], 'admin'>;
  onClose: () => void;
  className?: string;
}

function normalizeNotifications(notifications: NotificationItem[]): NotificationItem[] {
  const deduped = new Map<string, NotificationItem>();

  for (const notification of notifications) {
    deduped.set(notification.notification_id, notification);
  }

  return Array.from(deduped.values())
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 50);
}

function formatCreatedAt(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

export function NotificationPanel({
  isOpen,
  role,
  onClose,
  className = '',
}: NotificationPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const markRead = useMarkNotificationRead(role);
  const { data: cachedNotifications = [] } = useNotifications(role);

  const notifications = useMemo(
    () => normalizeNotifications(cachedNotifications),
    [cachedNotifications],
  );

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    panelRef.current?.focus();

    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) {
    return null;
  }

  const handleNotificationClick = (notification: NotificationItem) => {
    if (!notification.is_read) {
      markRead.mutate({ notificationId: notification.notification_id });
    }

    if (notification.report_id) {
      navigate(`/${role}/reports/${notification.report_id}`);
      onClose();
    }
  };

  return (
    <div
      ref={panelRef}
      tabIndex={-1}
      className={`absolute right-0 top-11 z-40 w-96 rounded-lg border border-clinical-border bg-clinical-surface shadow-lg focus:outline-none ${className}`}
      aria-label="Notifications"
    >
      <div className="border-b border-clinical-border px-4 py-3">
        <h2 className="text-sm font-semibold text-clinical-text-primary">Notifications</h2>
      </div>
      <div className="max-h-[400px] overflow-y-auto">
        {notifications.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-clinical-text-secondary">
            No notifications
          </div>
        ) : (
          <ul className="divide-y divide-clinical-border">
            {notifications.map((notification) => (
              <li key={notification.notification_id}>
                <button
                  type="button"
                  className="flex w-full gap-3 px-4 py-3 text-left hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-clinical-primary"
                  onClick={() => handleNotificationClick(notification)}
                >
                  <span
                    className={`mt-1 rounded-full p-1 ${
                      notification.is_read
                        ? 'bg-slate-100 text-clinical-text-muted'
                        : 'bg-clinical-primary-light text-clinical-primary'
                    }`}
                    aria-hidden="true"
                  >
                    <FileText className="h-4 w-4" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center justify-between gap-2">
                      <span className="truncate text-sm font-medium text-clinical-text-primary">
                        {notification.title}
                      </span>
                      <span className="shrink-0 text-xs text-clinical-text-muted">
                        {formatCreatedAt(notification.created_at)}
                      </span>
                    </span>
                    <span className="mt-1 line-clamp-2 block text-sm text-clinical-text-secondary">
                      {notification.message}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
