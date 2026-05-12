import { useParams } from 'react-router-dom';
import { PatientAnalyticsDashboard } from '../../components/charts/PatientAnalyticsDashboard';
import { RetryPanel } from '../../components/feedback/RetryPanel';
import { useAnalytics } from '../../hooks/useIntelligence';
import { normalizeApiError } from '../../lib/apiError';

export default function AnalyticsPage() {
  const { patientId = '' } = useParams();
  const analytics = useAnalytics(patientId);

  if (analytics.isError) {
    return <RetryPanel onRetry={() => void analytics.refetch()} message={normalizeApiError(analytics.error).message} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-clinical-text-primary">Analytics</h1>
        <p className="mt-1 text-sm text-clinical-text-secondary">Patient trend and abnormality review.</p>
      </div>

      <PatientAnalyticsDashboard analytics={analytics.data} isLoading={analytics.isLoading} />
    </div>
  );
}
