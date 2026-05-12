import { Link } from 'react-router-dom';
import { Card } from '../../components/ui/Card';
import { Skeleton } from '../../components/ui/Skeleton';
import { RetryPanel } from '../../components/feedback/RetryPanel';
import { EmptyState } from '../../components/ui/EmptyState';
import { useDoctorAssignments } from '../../hooks/useAssignments';
import { useAuth } from '../../hooks/useAuth';
import { useNotifications } from '../../hooks/useNotifications';
import { useDoctorReports } from '../../hooks/useReports';
import { normalizeApiError } from '../../lib/apiError';
import { getReportDisplayName } from '../../lib/reportName';

export default function DoctorDashboard() {
  const { user } = useAuth();
  const assignments = useDoctorAssignments();
  const reports = useDoctorReports();
  const notifications = useNotifications('doctor');

  if (assignments.isError || reports.isError) {
    return (
      <RetryPanel
        onRetry={() => {
          void assignments.refetch();
          void reports.refetch();
        }}
        message={normalizeApiError(assignments.error ?? reports.error).message}
      />
    );
  }

  const assignmentRows = assignments.data ?? [];
  const reportRows = reports.data ?? [];
  const hitlReports = reportRows.filter((report) => report.lifecycle_status === 'hitl_required');
  const verifiedReports = reportRows.filter((report) =>
    report.lifecycle_status === 'doctor_verified' || report.lifecycle_status === 'fully_verified',
  );
  const failedReports = reportRows.filter((report) => report.lifecycle_status === 'failed');
  const criticalAlerts = (notifications.data ?? []).filter((notification) =>
    notification.type.toLowerCase().includes('critical') || notification.title.toLowerCase().includes('critical'),
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-clinical-text-primary">Doctor Dashboard</h1>
        <p className="mt-1 text-sm text-clinical-text-secondary">
          {user?.full_name ?? 'Doctor'} · {user?.specialization ?? 'Specialization not set'} · {user?.verification_status?.replaceAll('_', ' ') ?? 'verification unknown'}
        </p>
        <p className="mt-1 text-sm text-clinical-text-secondary">
          {[user?.hospital_name, user?.department].filter(Boolean).join(' · ') || 'Hospital and department not set'}
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-5">
        {assignments.isLoading || reports.isLoading ? (
          <Skeleton variant="stat" rows={5} className="md:col-span-5 md:grid md:grid-cols-5 md:gap-4 md:space-y-0" />
        ) : (
          <>
            <Card>
              <p className="text-sm text-clinical-text-secondary">Assigned Reports</p>
              <p className="mt-2 text-2xl font-semibold">{reportRows.length}</p>
            </Card>
            <Card>
              <p className="text-sm text-clinical-text-secondary">Pending HITL Review</p>
              <p className="mt-2 text-2xl font-semibold">{hitlReports.length}</p>
            </Card>
            <Card>
              <p className="text-sm text-clinical-text-secondary">Verified Reports</p>
              <p className="mt-2 text-2xl font-semibold">{verifiedReports.length}</p>
            </Card>
            <Card>
              <p className="text-sm text-clinical-text-secondary">Failed Reports</p>
              <p className="mt-2 text-2xl font-semibold">{failedReports.length}</p>
            </Card>
            <Card>
              <p className="text-sm text-clinical-text-secondary">Critical Alerts</p>
              <p className="mt-2 text-2xl font-semibold">{criticalAlerts.length}</p>
            </Card>
          </>
        )}
      </div>

      <Card>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-semibold text-clinical-text-primary">Recent Reports</h2>
          <Link className="text-sm font-medium text-clinical-primary hover:underline" to="/doctor/reports">
            View all
          </Link>
        </div>
        {reports.isLoading ? (
          <Skeleton variant="card" rows={4} />
        ) : reportRows.length === 0 ? (
          <EmptyState title="No assigned reports yet" />
        ) : (
          <div className="space-y-2">
            {reportRows.slice(0, 5).map((report) => (
              <Link
                key={report.report_id}
                to={`/doctor/reports/${report.report_id}`}
                className="block rounded-md border border-clinical-border px-3 py-2 text-sm hover:bg-slate-50"
              >
                <span className="font-medium text-clinical-text-primary">{getReportDisplayName(report)}</span>
                <span className="ml-3 text-clinical-text-secondary">{report.lifecycle_status.replaceAll('_', ' ')}</span>
              </Link>
            ))}
          </div>
        )}
      </Card>

      <Card>
        <h2 className="text-base font-semibold text-clinical-text-primary">Analytics Snapshot</h2>
        <div className="mt-3 grid gap-3 text-sm md:grid-cols-3">
          <div>
            <p className="text-clinical-text-secondary">Active patient links</p>
            <p className="font-semibold">{assignmentRows.filter((assignment) => assignment.status === 'active').length}</p>
          </div>
          <div>
            <p className="text-clinical-text-secondary">Processing reports</p>
            <p className="font-semibold">{reportRows.filter((report) => report.lifecycle_status === 'processing').length}</p>
          </div>
          <div>
            <p className="text-clinical-text-secondary">Turnaround focus</p>
            <p className="font-semibold">{hitlReports.length > 0 ? 'Review HITL queue' : 'Queue clear'}</p>
          </div>
        </div>
      </Card>
    </div>
  );
}
