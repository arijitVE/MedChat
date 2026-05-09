import { useMemo, useState } from 'react';
import { Bell } from 'lucide-react';
import { useNotifications } from '../../hooks/useNotifications';
import { useAuthStore } from '../../store/authStore';
import { NotificationPanel } from './NotificationPanel';

function unreadLabel(count: number): string {
  return count > 99 ? '99+' : String(count);
}

export function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false);
  const user = useAuthStore((state) => state.user);
  const role = user?.role;
  const notificationRole = role === 'doctor' || role === 'patient' ? role : undefined;
  const { data: notifications = [] } = useNotifications(notificationRole);

  const unreadCount = useMemo(
    () => notifications.filter((notification) => !notification.is_read).length,
    [notifications],
  );

  if (!notificationRole) {
    return null;
  }

  return (
    <div className="relative">
      <button
        type="button"
        className="relative rounded-md p-2 text-clinical-text-secondary hover:bg-slate-100 hover:text-clinical-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-clinical-primary"
        aria-label={`Notifications, ${unreadCount} unread`}
        aria-expanded={isOpen}
        onClick={() => setIsOpen((open) => !open)}
      >
        <Bell className="h-5 w-5" aria-hidden="true" />
        {unreadCount > 0 ? (
          <span className="absolute -right-1 -top-1 rounded-full bg-clinical-critical px-1.5 py-0.5 text-[10px] font-semibold leading-none text-white">
            {unreadLabel(unreadCount)}
          </span>
        ) : null}
      </button>
      <NotificationPanel
        isOpen={isOpen}
        role={notificationRole}
        onClose={() => setIsOpen(false)}
      />
    </div>
  );
}
