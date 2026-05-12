import { useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { PatientAnalyticsDashboard } from '../../components/charts/PatientAnalyticsDashboard';
import { RetryPanel } from '../../components/feedback/RetryPanel';
import { ReportCard } from '../../components/report/ReportCard';
import { Card } from '../../components/ui/Card';
import { EmptyState } from '../../components/ui/EmptyState';
import { Skeleton } from '../../components/ui/Skeleton';
import { useDoctorAssignments } from '../../hooks/useAssignments';
import { useAnalytics } from '../../hooks/useIntelligence';
import { useDoctorReports } from '../../hooks/useReports';
import { normalizeApiError } from '../../lib/apiError';

export default function PatientDetailPage() {
  const { patientId = '' } = useParams();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'reports' | 'analytics'>('reports');
  const assignments = useDoctorAssignments();
  const analytics = useAnalytics(patientId);
  const reports = useDoctorReports({ patient_id: patientId });
  const assignment = useMemo(
    () => (assignments.data ?? []).find((item) => item.patient_id === patientId),
    [assignments.data, patientId],
  );

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
        reports.isError ? (
          <RetryPanel onRetry={() => void reports.refetch()} message={normalizeApiError(reports.error).message} />
        ) : reports.isLoading ? (
          <Skeleton variant="card" rows={5} />
        ) : (reports.data ?? []).length === 0 ? (
          <EmptyState title="No reports found for this patient" />
        ) : (
          <div className="grid gap-4">
            {(reports.data ?? []).map((report) => (
              <ReportCard
                key={report.report_id}
                report={report}
                onSelect={() => navigate(`/doctor/reports/${report.report_id}`)}
              />
            ))}
          </div>
        )
      ) : analytics.isError ? (
        <RetryPanel onRetry={() => void analytics.refetch()} message={normalizeApiError(analytics.error).message} />
      ) : (
        <PatientAnalyticsDashboard analytics={analytics.data} isLoading={analytics.isLoading} />
      )}
    </div>
  );
}
