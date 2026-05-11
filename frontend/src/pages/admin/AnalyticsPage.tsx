import { useQuery } from '@tanstack/react-query';
import { adminApi } from '../../api/admin';
import { Card } from '../../components/ui/Card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/Table';
import { queryKeys, staleTime } from '../../lib/queryKeys';
import { PageHeader, QueryState, StatGrid } from './AdminUtils';
import type { AdminMetricRow } from '../../types/admin';

function MetricTable({ title, rows }: { title: string; rows: AdminMetricRow[] }) {
  return (
    <Card>
      <h2 className="mb-4 text-base font-semibold text-clinical-text-primary">{title}</h2>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Label</TableHead>
            <TableHead>Count</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row) => (
            <TableRow key={row.label}>
              <TableCell>{row.label}</TableCell>
              <TableCell>{row.value}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  );
}

export default function AnalyticsPage() {
  const analytics = useQuery({
    queryKey: queryKeys.admin.analytics,
    queryFn: async () => (await adminApi.getAnalytics()).data,
    staleTime: staleTime.analytics,
  });

  return (
    <div className="space-y-6">
      <PageHeader title="Analytics" description="Operational analytics for users, reports, and processing." />
      <QueryState
        isLoading={analytics.isLoading}
        isError={analytics.isError}
        error={analytics.error}
        onRetry={() => void analytics.refetch()}
        isEmpty={!analytics.data}
        emptyTitle="No analytics available"
      >
        <StatGrid
          stats={[
            { label: 'Users', value: analytics.data?.total_users ?? 0 },
            { label: 'Doctors', value: analytics.data?.total_doctors ?? 0 },
            { label: 'Patients', value: analytics.data?.total_patients ?? 0 },
            { label: 'Reports', value: analytics.data?.total_reports ?? 0 },
            { label: 'Failed Jobs', value: analytics.data?.failed_jobs ?? 0 },
            { label: 'HITL Required', value: analytics.data?.hitl_required ?? 0 },
          ]}
        />
        <div className="grid gap-6 lg:grid-cols-3">
          <MetricTable title="Reports by Status" rows={analytics.data?.reports_by_status ?? []} />
          <MetricTable title="Users by Role" rows={analytics.data?.users_by_role ?? []} />
          <MetricTable title="Reports by Type" rows={analytics.data?.reports_by_document_type ?? []} />
        </div>
      </QueryState>
    </div>
  );
}
