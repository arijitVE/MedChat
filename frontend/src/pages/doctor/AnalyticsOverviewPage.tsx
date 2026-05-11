import { Link } from 'react-router-dom';
import { RetryPanel } from '../../components/feedback/RetryPanel';
import { Card } from '../../components/ui/Card';
import { EmptyState } from '../../components/ui/EmptyState';
import { Skeleton } from '../../components/ui/Skeleton';
import { useDoctorAssignments } from '../../hooks/useAssignments';
import { useDoctorReports } from '../../hooks/useReports';
import { normalizeApiError } from '../../lib/apiError';

export default function AnalyticsOverviewPage() {
  const assignments = useDoctorAssignments();
  const reports = useDoctorReports();

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

  const reportRows = reports.data ?? [];
  const activePatientIds = new Set((assignments.data ?? []).filter((item) => item.status === 'active').map((item) => item.patient_id));
  const byStatus = reportRows.reduce<Record<string, number>>((acc, report) => {
    acc[report.lifecycle_status] = (acc[report.lifecycle_status] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-clinical-text-primary">Analytics</h1>
        <p className="mt-1 text-sm text-clinical-text-secondary">Doctor-wide workflow and patient monitoring snapshot.</p>
      </div>

      {assignments.isLoading || reports.isLoading ? (
        <Skeleton variant="card" rows={4} />
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-4">
            <Card>
              <p className="text-sm text-clinical-text-secondary">Active Patients</p>
              <p className="mt-2 text-2xl font-semibold">{activePatientIds.size}</p>
            </Card>
            <Card>
              <p className="text-sm text-clinical-text-secondary">Reports</p>
              <p className="mt-2 text-2xl font-semibold">{reportRows.length}</p>
            </Card>
            <Card>
              <p className="text-sm text-clinical-text-secondary">HITL Required</p>
              <p className="mt-2 text-2xl font-semibold">{byStatus.hitl_required ?? 0}</p>
            </Card>
            <Card>
              <p className="text-sm text-clinical-text-secondary">Failed</p>
              <p className="mt-2 text-2xl font-semibold">{byStatus.failed ?? 0}</p>
            </Card>
          </div>

          <Card>
            <h2 className="text-base font-semibold text-clinical-text-primary">Patient-Specific Analytics</h2>
            <p className="mt-2 text-sm text-clinical-text-secondary">
              Open a patient profile to review longitudinal trends, abnormalities, and field-level analytics.
            </p>
            {activePatientIds.size === 0 ? (
              <div className="mt-4">
                <EmptyState title="No active patient assignments yet" />
              </div>
            ) : (
              <Link className="mt-4 inline-block text-sm font-medium text-clinical-primary hover:underline" to="/doctor/patients">
                Select patient
              </Link>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
