import { useNavigate } from 'react-router-dom';
import { Card } from '../../components/ui/Card';
import { EmptyState } from '../../components/ui/EmptyState';
import { Skeleton } from '../../components/ui/Skeleton';
import { RetryPanel } from '../../components/feedback/RetryPanel';
import { ReportCard } from '../../components/report/ReportCard';
import { useAuth } from '../../hooks/useAuth';
import { useNotifications } from '../../hooks/useNotifications';
import { useMyReports } from '../../hooks/useReports';
import { normalizeApiError } from '../../lib/apiError';

export default function PatientDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const reports = useMyReports();
  const notifications = useNotifications('patient');

  if (reports.isError) {
    return (
      <RetryPanel
        onRetry={() => void reports.refetch()}
        message={normalizeApiError(reports.error).message}
      />
    );
  }

  const allReports = reports.data ?? [];
  const releasedReports = [...allReports].sort(
    (a, b) => new Date(b.first_uploaded_at).getTime() - new Date(a.first_uploaded_at).getTime(),
  );
  const verifiedReports = allReports.filter((report) =>
    report.lifecycle_status === 'fully_verified' || report.lifecycle_status === 'doctor_verified',
  );
  const processingReports = allReports.filter((report) =>
    report.lifecycle_status === 'processing' || report.lifecycle_status === 'uploaded',
  );
  const failedReports = allReports.filter((report) => report.lifecycle_status === 'failed');
  const latestNotifications = (notifications.data ?? []).slice(0, 3);

  return (
    <div className="space-y-6">
      <Card>
        <h1 className="text-lg font-semibold text-clinical-text-primary">
          Patient Dashboard
        </h1>
        <p className="mt-1 text-sm text-clinical-text-secondary">
          Patient ID: <span className="font-mono">{user?.patient_uid ?? user?.user_id ?? '-'}</span>
        </p>
      </Card>

      <div className="grid gap-4 md:grid-cols-4">
        {reports.isLoading ? (
          <Skeleton variant="stat" rows={4} className="md:col-span-4 md:grid md:grid-cols-4 md:gap-4 md:space-y-0" />
        ) : (
          <>
            <Card>
              <p className="text-sm text-clinical-text-secondary">Total Reports</p>
              <p className="mt-2 text-2xl font-semibold">{allReports.length}</p>
            </Card>
            <Card>
              <p className="text-sm text-clinical-text-secondary">Processing</p>
              <p className="mt-2 text-2xl font-semibold">{processingReports.length}</p>
            </Card>
            <Card>
              <p className="text-sm text-clinical-text-secondary">Verified</p>
              <p className="mt-2 text-2xl font-semibold">{verifiedReports.length}</p>
            </Card>
            <Card>
              <p className="text-sm text-clinical-text-secondary">Failed</p>
              <p className="mt-2 text-2xl font-semibold">{failedReports.length}</p>
            </Card>
          </>
        )}
      </div>

      <section className="space-y-4">
        <h2 className="text-base font-semibold text-clinical-text-primary">Recent Reports</h2>
        {reports.isLoading ? (
          <Skeleton variant="card" rows={5} />
        ) : releasedReports.length === 0 ? (
          <EmptyState title="No reports uploaded yet. Upload your first medical report to begin AI-powered analysis and health tracking." />
        ) : (
          <div className="grid gap-4">
            {releasedReports.slice(0, 5).map((report) => (
              <ReportCard
                key={report.report_id}
                report={report}
                onSelect={() => navigate(`/patient/reports/${report.report_id}`)}
              />
            ))}
          </div>
        )}
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <h2 className="text-base font-semibold text-clinical-text-primary">Notifications</h2>
          <div className="mt-4 space-y-3">
            {latestNotifications.length === 0 ? (
              <p className="text-sm text-clinical-text-secondary">No recent notifications.</p>
            ) : (
              latestNotifications.map((notification) => (
                <div key={notification.notification_id} className="rounded-md border border-clinical-border px-3 py-2">
                  <p className="text-sm font-medium text-clinical-text-primary">{notification.title}</p>
                  <p className="mt-1 text-sm text-clinical-text-secondary">{notification.message}</p>
                </div>
              ))
            )}
          </div>
        </Card>
        <Card>
          <h2 className="text-base font-semibold text-clinical-text-primary">Health Trends Snapshot</h2>
          <p className="mt-2 text-sm text-clinical-text-secondary">
            Track values like glucose, hemoglobin, cholesterol, and blood pressure from your uploaded reports.
          </p>
          <button
            type="button"
            className="mt-4 text-sm font-medium text-clinical-primary hover:underline"
            onClick={() => navigate('/patient/trends')}
          >
            View trends
          </button>
        </Card>
      </div>
    </div>
  );
}
