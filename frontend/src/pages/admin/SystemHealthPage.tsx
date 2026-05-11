import { useQuery } from '@tanstack/react-query';
import { adminApi } from '../../api/admin';
import { queryKeys, staleTime } from '../../lib/queryKeys';
import { PageHeader, QueryState, StatGrid } from './AdminUtils';

export default function SystemHealthPage() {
  const health = useQuery({
    queryKey: queryKeys.admin.systemHealth,
    queryFn: async () => (await adminApi.getSystemHealth()).data,
    staleTime: staleTime.adminStats,
  });

  return (
    <div className="space-y-6">
      <PageHeader title="System Health" description="API, database, and processing health." />
      <QueryState
        isLoading={health.isLoading}
        isError={health.isError}
        error={health.error}
        onRetry={() => void health.refetch()}
        isEmpty={!health.data}
        emptyTitle="System health is unavailable"
      >
        <StatGrid
          stats={[
            { label: 'API', value: health.data?.api_status ?? '-' },
            { label: 'Database', value: health.data?.database_status ?? '-' },
            { label: 'Processing Reports', value: health.data?.total_processing_reports ?? 0 },
            { label: 'Failed Reports', value: health.data?.total_failed_reports ?? 0 },
            { label: 'Failed Jobs', value: health.data?.total_failed_jobs ?? 0 },
          ]}
        />
      </QueryState>
    </div>
  );
}
