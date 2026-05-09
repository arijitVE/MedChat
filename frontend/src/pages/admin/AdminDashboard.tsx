import { useQuery } from '@tanstack/react-query';
import { adminApi } from '../../api/admin';
import { RetryPanel } from '../../components/feedback/RetryPanel';
import { Card } from '../../components/ui/Card';
import { Skeleton } from '../../components/ui/Skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/Table';
import { normalizeApiError } from '../../lib/apiError';
import { queryKeys, staleTime } from '../../lib/queryKeys';

const statLabels = [
  ['total_doctors', 'Total Doctors'],
  ['total_patients', 'Total Patients'],
  ['total_reports', 'Total Reports'],
  ['processing_now', 'Processing'],
  ['hitl_pending', 'HITL Pending'],
  ['fully_verified', 'Fully Verified'],
] as const;

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(new Date(value));
}

export default function AdminDashboard() {
  const stats = useQuery({
    queryKey: queryKeys.admin.stats,
    queryFn: async () => {
      try {
        const response = await adminApi.getStats();
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    staleTime: staleTime.adminStats,
  });

  const recentUsers = useQuery({
    queryKey: queryKeys.admin.users({ page: 1, page_size: 5 }),
    queryFn: async () => {
      try {
        const response = await adminApi.getUsers({ page: 1, page_size: 5 });
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    staleTime: staleTime.usersList,
  });

  if (stats.isError) {
    return <RetryPanel onRetry={() => void stats.refetch()} message={normalizeApiError(stats.error).message} />;
  }

  if (recentUsers.isError) {
    return <RetryPanel onRetry={() => void recentUsers.refetch()} message={normalizeApiError(recentUsers.error).message} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-clinical-text-primary">Admin Dashboard</h1>
        <p className="mt-1 text-sm text-clinical-text-secondary">System health and recent account activity.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {stats.isLoading || !stats.data ? (
          <Skeleton variant="stat" rows={6} className="md:col-span-3 md:grid md:grid-cols-3 md:gap-4 md:space-y-0" />
        ) : (
          statLabels.map(([key, label]) => (
            <Card key={key}>
              <p className="text-sm text-clinical-text-secondary">{label}</p>
              <p className="mt-2 text-2xl font-semibold text-clinical-text-primary">{stats.data[key]}</p>
            </Card>
          ))
        )}
      </div>

      <section className="space-y-4">
        <h2 className="text-base font-semibold text-clinical-text-primary">Recent Signups</h2>
        {recentUsers.isLoading ? (
          <Skeleton variant="table-row" rows={5} />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(recentUsers.data?.items ?? []).map((user) => (
                <TableRow key={user.user_id}>
                  <TableCell className="font-medium">{user.full_name}</TableCell>
                  <TableCell>{user.email}</TableCell>
                  <TableCell className="capitalize">{user.role}</TableCell>
                  <TableCell>{user.is_active ? 'Active' : 'Inactive'}</TableCell>
                  <TableCell>{formatDate(user.created_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </section>
    </div>
  );
}
