import { Link } from 'react-router-dom';
import { Card } from '../../components/ui/Card';
import { Skeleton } from '../../components/ui/Skeleton';
import { RetryPanel } from '../../components/feedback/RetryPanel';
import { EmptyState } from '../../components/ui/EmptyState';
import { useDoctorAssignments } from '../../hooks/useAssignments';
import { normalizeApiError } from '../../lib/apiError';

export default function DoctorDashboard() {
  const assignments = useDoctorAssignments();

  if (assignments.isError) {
    return (
      <RetryPanel
        onRetry={() => void assignments.refetch()}
        message={normalizeApiError(assignments.error).message}
      />
    );
  }

  const assignmentRows = assignments.data ?? [];
  const activeAssignments = assignmentRows.filter((assignment) => assignment.status === 'active').length;
  const pendingAssignments = assignmentRows.filter((assignment) => assignment.status === 'pending').length;
  const rejectedAssignments = assignmentRows.filter((assignment) => assignment.status === 'rejected').length;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-clinical-text-primary">Doctor Dashboard</h1>
        <p className="mt-1 text-sm text-clinical-text-secondary">Recent clinical activity</p>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        {assignments.isLoading ? (
          <Skeleton variant="stat" rows={4} className="md:col-span-4 md:grid md:grid-cols-4 md:gap-4 md:space-y-0" />
        ) : (
          <>
            <Card>
              <p className="text-sm text-clinical-text-secondary">Assignments</p>
              <p className="mt-2 text-2xl font-semibold">{assignmentRows.length}</p>
            </Card>
            <Card>
              <p className="text-sm text-clinical-text-secondary">Active</p>
              <p className="mt-2 text-2xl font-semibold">{activeAssignments}</p>
            </Card>
            <Card>
              <p className="text-sm text-clinical-text-secondary">Pending</p>
              <p className="mt-2 text-2xl font-semibold">{pendingAssignments}</p>
            </Card>
            <Card>
              <p className="text-sm text-clinical-text-secondary">Rejected</p>
              <p className="mt-2 text-2xl font-semibold">{rejectedAssignments}</p>
            </Card>
          </>
        )}
      </div>

      <Card>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-semibold text-clinical-text-primary">Recent Reports</h2>
          <Link className="text-sm font-medium text-clinical-primary hover:underline" to="/doctor/upload">
            Upload report
          </Link>
        </div>
        {/* TODO: restore recent reports when the backend exposes a doctor report list route. */}
        <EmptyState title="Recent reports are not exposed by the current backend routes" />
      </Card>
    </div>
  );
}
