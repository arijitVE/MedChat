import { Menu } from 'lucide-react';
import { Button } from '../ui/Button';
import { NotificationBell } from '../notifications/NotificationBell';
import { useAuthStore } from '../../store/authStore';
import { useUIStore } from '../../store/uiStore';

export function Topbar() {
  const user = useAuthStore((state) => state.user);
  const sidebarOpen = useUIStore((state) => state.sidebarOpen);
  const setSidebarOpen = useUIStore((state) => state.setSidebarOpen);

  return (
    <header className="flex h-14 items-center justify-between border-b border-clinical-border bg-clinical-surface px-4">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          className="min-h-9 px-2"
          aria-label={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
          onClick={() => setSidebarOpen(!sidebarOpen)}
        >
          <Menu className="h-5 w-5" aria-hidden="true" />
        </Button>
        <span className="text-sm font-medium text-clinical-text-secondary">
          {user?.full_name ?? 'HDMIS'}
        </span>
      </div>
      <div className="flex items-center gap-3">
        <NotificationBell />
      </div>
    </header>
  );
}
