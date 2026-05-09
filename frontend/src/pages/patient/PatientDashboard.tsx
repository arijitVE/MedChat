import { useNavigate } from 'react-router-dom';
import { Card } from '../../components/ui/Card';
import { Skeleton } from '../../components/ui/Skeleton';
import { RetryPanel } from '../../components/feedback/RetryPanel';
import { ReportCard } from '../../components/report/ReportCard';
import { useAuth } from '../../hooks/useAuth';
import { useMyReports } from '../../hooks/useReports';
import { normalizeApiError } from '../../lib/apiError';

export default function PatientDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const reports = useMyReports();

  if (reports.isError) {
    return (
      <RetryPanel
        onRetry={() => void reports.refetch()}
        message={normalizeApiError(reports.error).message}
      />
    );
  }

  const releasedReports = [...(reports.data?.filter((report) => report.released_to_patient) ?? [])].sort(
    (a, b) => new Date(b.first_uploaded_at).getTime() - new Date(a.first_uploaded_at).getTime(),
  );
  const verifiedReports = releasedReports.filter((report) => report.lifecycle_status === 'fully_verified');
  const processingReports = reports.data?.filter((report) => report.lifecycle_status === 'processing') ?? [];

  return (
    <div className="space-y-6">
      <Card>
        <h1 className="text-lg font-semibold text-clinical-text-primary">
          Welcome, {user?.full_name ?? 'Patient'}
        </h1>
        <p className="mt-1 text-sm text-clinical-text-secondary">
          Review released reports, trends, and patient-friendly explanations.
        </p>
      </Card>

      <div className="grid gap-4 md:grid-cols-3">
        {reports.isLoading ? (
          <Skeleton variant="stat" rows={3} className="md:col-span-3 md:grid md:grid-cols-3 md:gap-4 md:space-y-0" />
        ) : (
          <>
            <Card>
              <p className="text-sm text-clinical-text-secondary">Released Reports</p>
              <p className="mt-2 text-2xl font-semibold">{releasedReports.length}</p>
            </Card>
            <Card>
              <p className="text-sm text-clinical-text-secondary">Fully Verified</p>
              <p className="mt-2 text-2xl font-semibold">{verifiedReports.length}</p>
            </Card>
            <Card>
              <p className="text-sm text-clinical-text-secondary">Processing</p>
              <p className="mt-2 text-2xl font-semibold">{processingReports.length}</p>
            </Card>
          </>
        )}
      </div>

      <section className="space-y-4">
        <h2 className="text-base font-semibold text-clinical-text-primary">Recent Reports</h2>
        {reports.isLoading ? (
          <Skeleton variant="card" rows={5} />
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
    </div>
  );
}
