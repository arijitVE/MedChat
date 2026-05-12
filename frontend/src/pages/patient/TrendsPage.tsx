import { PatientAnalyticsDashboard } from '../../components/charts/PatientAnalyticsDashboard';
import { RetryPanel } from '../../components/feedback/RetryPanel';
import { useMyAnalytics } from '../../hooks/useIntelligence';
import { normalizeApiError } from '../../lib/apiError';

export default function TrendsPage() {
  const analytics = useMyAnalytics();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-clinical-text-primary">Trends</h1>
        <p className="mt-1 text-sm text-clinical-text-secondary">
          Visualize your report values, reference ranges, and abnormal findings from structured report data.
        </p>
      </div>

      {analytics.isError ? (
        <RetryPanel onRetry={() => void analytics.refetch()} message={normalizeApiError(analytics.error).message} />
      ) : (
        <PatientAnalyticsDashboard analytics={analytics.data} isLoading={analytics.isLoading} />
      )}
    </div>
  );
}
