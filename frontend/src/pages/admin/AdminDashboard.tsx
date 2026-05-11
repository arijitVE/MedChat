import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { adminApi } from '../../api/admin';
import { Card } from '../../components/ui/Card';
import { queryKeys, staleTime } from '../../lib/queryKeys';
import { PageHeader, QueryState, StatGrid } from './AdminUtils';

const quickLinks = [
  { label: 'Users', to: '/admin/users' },
  { label: 'Assign Doctor', to: '/admin/assignments' },
  { label: 'Reports', to: '/admin/reports' },
  { label: 'Failed Jobs', to: '/admin/failed-jobs' },
  { label: 'HITL Queue', to: '/admin/hitl' },
  { label: 'System Health', to: '/admin/system-health' },
];

export default function AdminDashboard() {
  const stats = useQuery({
    queryKey: queryKeys.admin.stats,
    queryFn: async () => (await adminApi.getDashboard()).data,
    staleTime: staleTime.adminStats,
  });

  return (
    <div className="space-y-6">
      <PageHeader title="Admin Dashboard" description="System overview and operational shortcuts." />

      <QueryState
        isLoading={stats.isLoading}
        isError={stats.isError}
        error={stats.error}
        onRetry={() => void stats.refetch()}
        isEmpty={!stats.data}
        emptyTitle="No admin statistics available"
      >
        <StatGrid
          stats={[
            { label: 'Doctors', value: stats.data?.total_doctors ?? 0 },
            { label: 'Patients', value: stats.data?.total_patients ?? 0 },
            { label: 'Reports', value: stats.data?.total_reports ?? 0 },
            { label: 'Processing', value: stats.data?.reports_processing ?? 0 },
            { label: 'HITL Required', value: stats.data?.reports_hitl_required ?? 0 },
            { label: 'Fully Verified', value: stats.data?.reports_fully_verified ?? 0 },
            { label: 'Active Assignments', value: stats.data?.assignments_active ?? 0 },
            { label: 'Pending Assignments', value: stats.data?.assignments_pending ?? 0 },
          ]}
        />
      </QueryState>

      <Card>
        <h2 className="text-base font-semibold text-clinical-text-primary">Admin Areas</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {quickLinks.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className="rounded-md border border-clinical-border px-4 py-3 text-sm font-medium text-clinical-primary hover:bg-slate-50"
            >
              {link.label}
            </Link>
          ))}
        </div>
      </Card>
    </div>
  );
}
