import { useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { AbnormalityPanel } from '../../components/charts/AbnormalityPanel';
import { TrendLineChart } from '../../components/charts/TrendLineChart';
import { RetryPanel } from '../../components/feedback/RetryPanel';
import { ReportCard } from '../../components/report/ReportCard';
import { Card } from '../../components/ui/Card';
import { Skeleton } from '../../components/ui/Skeleton';
import { usePatientProfile } from '../../hooks/useAssignments';
import { useAnalytics, useTrend } from '../../hooks/useIntelligence';
import { useDoctorPatientReports } from '../../hooks/useReports';
import { normalizeApiError } from '../../lib/apiError';

export default function PatientDetailPage() {
  const { patientId = '' } = useParams();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'reports' | 'analytics'>('reports');
  const profile = usePatientProfile(patientId);
  const reports = useDoctorPatientReports(patientId);
  const analytics = useAnalytics(patientId);
  const selectedField = useMemo(() => {
    const field = analytics.data?.abnormal_fields[0] ?? analytics.data?.normal_fields[0];
    return field?.name ?? '';
  }, [analytics.data]);
  const trend = useTrend(patientId, selectedField);

  if (profile.isError) {
    return <RetryPanel onRetry={() => void profile.refetch()} message={normalizeApiError(profile.error).message} />;
  }

  return (
    <div className="space-y-6">
      <Card>
        {profile.isLoading ? (
          <Skeleton variant="text" rows={3} />
        ) : (
          <div>
            <h1 className="text-lg font-semibold text-clinical-text-primary">{profile.data?.full_name}</h1>
            <div className="mt-2 flex flex-wrap gap-4 text-sm text-clinical-text-secondary">
              <span>UID: {profile.data?.patient_uid}</span>
              <span>DOB: {profile.data?.date_of_birth ?? '-'}</span>
              <span>Sex: {profile.data?.sex ?? '-'}</span>
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
          <Skeleton variant="card" rows={4} />
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
