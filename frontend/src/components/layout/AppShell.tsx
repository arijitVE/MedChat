import { Outlet } from 'react-router-dom';
import { RealtimeProvider } from '../../providers/RealtimeProvider';
import { useUIStore } from '../../store/uiStore';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';

export function AppShell() {
  const sidebarOpen = useUIStore((state) => state.sidebarOpen);

  return (
    <RealtimeProvider>
      <div className="min-h-screen bg-clinical-bg text-clinical-text-primary">
        <Sidebar />
        <div className={sidebarOpen ? 'min-h-screen pl-64' : 'min-h-screen'}>
          <Topbar />
          <main className="p-6">
            <Outlet />
          </main>
        </div>
      </div>
    </RealtimeProvider>
  );
}
