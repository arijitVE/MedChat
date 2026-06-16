import { useQuery } from '@tanstack/react-query';
import { adminApi } from '../../api/admin';
import { Card } from '../../components/ui/Card';
import { queryKeys, staleTime } from '../../lib/queryKeys';
import { PageHeader, QueryState } from './AdminUtils';

export default function SettingsPage() {
  const settings = useQuery({
    queryKey: queryKeys.admin.settings,
    queryFn: async () => (await adminApi.getSettings()).data,
    staleTime: staleTime.adminStats,
  });

  return (
    <div className="space-y-6">
      <PageHeader title="Settings" description="Read-only runtime configuration summary." />
      <QueryState
        isLoading={settings.isLoading}
        isError={settings.isError}
        error={settings.error}
        onRetry={() => void settings.refetch()}
        isEmpty={!settings.data}
        emptyTitle="Settings are unavailable"
      >
        <Card>
          <dl className="grid gap-4 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-clinical-text-secondary">Storage path</dt>
              <dd className="mt-1 font-medium">{settings.data?.storage_path}</dd>
            </div>
            <div>
              <dt className="text-clinical-text-secondary">Max file size</dt>
              <dd className="mt-1 font-medium">{settings.data?.max_file_size_mb} MB</dd>
            </div>
            <div>
              <dt className="text-clinical-text-secondary">JWT expiry</dt>
              <dd className="mt-1 font-medium">{settings.data?.jwt_expiry_minutes} minutes</dd>
            </div>
            <div>
              <dt className="text-clinical-text-secondary">Rate limit storage</dt>
              <dd className="mt-1 font-medium">{settings.data?.rate_limit_storage}</dd>
            </div>
            <div>
              <dt className="text-clinical-text-secondary">OpenAI configured</dt>
              <dd className="mt-1 font-medium">{settings.data?.openai_configured ? 'Yes' : 'No'}</dd>
            </div>
          </dl>
        </Card>
      </QueryState>
    </div>
  );
}
