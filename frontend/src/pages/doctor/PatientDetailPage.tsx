import { useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { AbnormalityPanel } from '../../components/charts/AbnormalityPanel';
import { TrendLineChart } from '../../components/charts/TrendLineChart';
import { RetryPanel } from '../../components/feedback/RetryPanel';
import { Card } from '../../components/ui/Card';
import { EmptyState } from '../../components/ui/EmptyState';
import { Skeleton } from '../../components/ui/Skeleton';
import { useDoctorAssignments } from '../../hooks/useAssignments';
import { useAnalytics, useTrend } from '../../hooks/useIntelligence';
import { normalizeApiError } from '../../lib/apiError';

export default function PatientDetailPage() {
  const { patientId = '' } = useParams();
  const [activeTab, setActiveTab] = useState<'reports' | 'analytics'>('reports');
  const assignments = useDoctorAssignments();
  const analytics = useAnalytics(patientId);
  const assignment = useMemo(
    () => (assignments.data ?? []).find((item) => item.patient_id === patientId),
    [assignments.data, patientId],
  );
  const selectedField = useMemo(() => {
    const field = analytics.data?.abnormal_fields[0] ?? analytics.data?.normal_fields[0];
    return field?.name ?? '';
  }, [analytics.data]);
  const trend = useTrend(patientId, selectedField);

  if (assignments.isError) {
    return <RetryPanel onRetry={() => void assignments.refetch()} message={normalizeApiError(assignments.error).message} />;
  }

  return (
    <div className="space-y-6">
      <Card>
        {assignments.isLoading ? (
          <Skeleton variant="text" rows={3} />
        ) : (
          <div>
            <h1 className="text-lg font-semibold text-clinical-text-primary">Patient {patientId}</h1>
            <div className="mt-2 flex flex-wrap gap-4 text-sm text-clinical-text-secondary">
              <span>Assignment: {assignment?.status ?? 'not found'}</span>
              <span>Assigned by: {assignment?.assigned_by ?? '-'}</span>
            </div>
          </div>
        )}
      </Card>

      <div className="flex gap-2" role="tablist" aria-label="Patient detail tabs">
        <button
          type="button"
          className={`rounded-md px-4 py-2 text-sm font-medium ${activeTab === 'reports' ? 'bg-clinical-primary text-white' : 'bg-clinical-surface text-clinical-text-secondary'}`}
          onClick={() => setActiveTab('reports')}
        >
          Reports
        </button>
        <button
          type="button"
          className={`rounded-md px-4 py-2 text-sm font-medium ${activeTab === 'analytics' ? 'bg-clinical-primary text-white' : 'bg-clinical-surface text-clinical-text-secondary'}`}
          onClick={() => setActiveTab('analytics')}
        >
          Analytics
        </button>
      </div>

      {activeTab === 'reports' ? (
        <>
          {/* TODO: restore this list when the backend exposes a doctor route for patient reports. */}
          <EmptyState title="Patient report lists are not exposed by the current backend routes" />
        </>
      ) : analytics.isError ? (
        <RetryPanel onRetry={() => void analytics.refetch()} message={normalizeApiError(analytics.error).message} />
      ) : (
        <div className="grid gap-6">
          <AbnormalityPanel
            abnormalFields={analytics.data?.abnormal_fields ?? []}
            normalFields={analytics.data?.normal_fields ?? []}
            isLoading={analytics.isLoading}
          />
          {selectedField ? (
            <TrendLineChart
              data={trend.data?.data_points ?? []}
              meta={trend.data?.chart_json.meta ?? { label: selectedField, unit: '', ref_low: null, ref_high: null }}
              insight={trend.data?.insight}
              trendDirection={trend.data?.trend_direction}
              isLoading={trend.isLoading}
            />
          ) : null}
        </div>
      )}
    </div>
  );
}
