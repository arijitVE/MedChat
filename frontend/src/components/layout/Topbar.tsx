import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Menu } from 'lucide-react';
import { Button } from '../ui/Button';
import { NotificationBell } from '../notifications/NotificationBell';
import { logout as apiLogout } from '../../api/auth';
import { useAuthStore } from '../../store/authStore';
import { useUIStore } from '../../store/uiStore';

export function Topbar() {
  const user = useAuthStore((state) => state.user);
  const clearAuth = useAuthStore((state) => state.clearAuth);
  const sidebarOpen = useUIStore((state) => state.sidebarOpen);
  const setSidebarOpen = useUIStore((state) => state.setSidebarOpen);
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  const handleLogout = async () => {
    try {
      await apiLogout();
    } catch {
      // Clear local auth state even if the server-side logout request fails.
    } finally {
      clearAuth();
      setMenuOpen(false);
      navigate('/login', { replace: true });
    }
  };

  const accountPath = user?.role === 'patient'
    ? '/patient/account'
    : user?.role === 'doctor'
      ? '/doctor/account'
      : `/${user?.role ?? 'login'}`;

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
        {user ? (
          <div className="relative">
            <button
              type="button"
              className="rounded-md px-2 py-1 text-sm font-medium text-clinical-text-secondary hover:bg-slate-100 hover:text-clinical-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-clinical-primary"
              onClick={() => setMenuOpen((open) => !open)}
              aria-expanded={menuOpen}
              aria-haspopup="menu"
            >
              {user.email}
            </button>
            {menuOpen ? (
              <div
                className="absolute right-0 top-full z-40 mt-2 w-48 rounded-md border border-clinical-border bg-clinical-surface py-1 text-sm shadow-lg"
                role="menu"
              >
                <button
                  type="button"
                  className="block w-full px-3 py-2 text-left text-clinical-text-primary hover:bg-slate-50"
                  onClick={() => {
                    setMenuOpen(false);
                    navigate(accountPath);
                  }}
                  role="menuitem"
                >
                  My Account
                </button>
                <div className="my-1 border-t border-clinical-border" />
                <button
                  type="button"
                  className="block w-full px-3 py-2 text-left text-clinical-critical hover:bg-clinical-critical-bg"
                  onClick={() => void handleLogout()}
                  role="menuitem"
                >
                  Logout
                </button>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </header>
  );
}
