import { NavLink } from 'react-router-dom';
import type { LucideIcon } from 'lucide-react';
import {
  BarChart3,
  Activity,
  Bell,
  FileText,
  Home,
  LogOut,
  MessageSquare,
  Upload,
  Users,
  ClipboardList,
  User as UserIcon,
  Settings,
  ShieldCheck,
  Stethoscope,
  UserRound,
  ClipboardCheck,
} from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import { useUIStore } from '../../store/uiStore';
import type { User } from '../../types/auth';

interface SidebarLink {
  to: string;
  label: string;
  icon: LucideIcon;
}

const linksByRole: Record<User['role'], SidebarLink[]> = {
  doctor: [
    { to: '/doctor', label: 'Dashboard', icon: Home },
    { to: '/doctor/patients', label: 'Patients', icon: Users },
    { to: '/doctor/reports', label: 'Reports', icon: FileText },
    { to: '/doctor/upload', label: 'Upload Report', icon: Upload },
    { to: '/doctor/hitl', label: 'HITL Queue', icon: ClipboardList },
    { to: '/doctor/analytics', label: 'Analytics', icon: BarChart3 },
    { to: '/doctor/notifications', label: 'Notifications', icon: Bell },
    { to: '/doctor/account', label: 'Account/Profile', icon: UserIcon },
    { to: '/doctor/logout', label: 'Logout', icon: LogOut },
  ],
  patient: [
    { to: '/patient', label: 'Dashboard', icon: Home },
    { to: '/patient/reports', label: 'Reports', icon: FileText },
    { to: '/patient/trends', label: 'Trends', icon: BarChart3 },
    { to: '/patient/chat', label: 'Chat Assistant', icon: MessageSquare },
    { to: '/patient/account', label: 'Account', icon: UserIcon },
  ],
  admin: [
    { to: '/admin', label: 'Dashboard', icon: Home },
    { to: '/admin/users', label: 'Users', icon: Users },
    { to: '/admin/doctors', label: 'Doctors', icon: Stethoscope },
    { to: '/admin/patients', label: 'Patients', icon: UserRound },
    { to: '/admin/assignments', label: 'Assign Doctor', icon: ClipboardCheck },
    { to: '/admin/reports', label: 'Reports', icon: FileText },
    { to: '/admin/failed-jobs', label: 'Failed Jobs', icon: Activity },
    { to: '/admin/hitl', label: 'HITL Overview', icon: ClipboardList },
    { to: '/admin/analytics', label: 'Analytics', icon: BarChart3 },
    { to: '/admin/notifications', label: 'Notifications', icon: Bell },
    { to: '/admin/audit-logs', label: 'Audit Logs', icon: ShieldCheck },
    { to: '/admin/system-health', label: 'System Health', icon: Activity },
    { to: '/admin/settings', label: 'Settings', icon: Settings },
    { to: '/admin/logout', label: 'Logout', icon: LogOut },
  ],
};

export function Sidebar() {
  const user = useAuthStore((state) => state.user);
  const sidebarOpen = useUIStore((state) => state.sidebarOpen);

  if (!user || !sidebarOpen) {
    return null;
  }

  const links = linksByRole[user.role];

  return (
    <aside className="fixed inset-y-0 left-0 z-30 w-64 border-r border-clinical-border bg-clinical-surface">
      <div className="flex h-14 items-center border-b border-clinical-border px-6">
        <span className="text-sm font-semibold text-clinical-text-primary">HDMIS</span>
      </div>
      <nav className="space-y-1 p-3" aria-label="Primary navigation">
        {links.map((link) => {
          const Icon = link.icon;

          return (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to.split('/').length === 2}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium outline-none transition-colors focus-visible:ring-2 focus-visible:ring-clinical-primary ${
                  isActive
                    ? 'bg-clinical-primary-light text-clinical-primary'
                    : 'text-clinical-text-secondary hover:bg-slate-100 hover:text-clinical-text-primary'
                }`
              }
            >
              <Icon className="h-4 w-4" aria-hidden="true" />
              <span>{link.label}</span>
            </NavLink>
          );
        })}
      </nav>
    </aside>
  );
}
