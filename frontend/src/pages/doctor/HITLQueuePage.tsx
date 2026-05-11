import { useNavigate } from 'react-router-dom';
import { RetryPanel } from '../../components/feedback/RetryPanel';
import { ReportCard } from '../../components/report/ReportCard';
import { EmptyState } from '../../components/ui/EmptyState';
import { Skeleton } from '../../components/ui/Skeleton';
import { useDoctorReports } from '../../hooks/useReports';
import { normalizeApiError } from '../../lib/apiError';

export default function HITLQueuePage() {
  const navigate = useNavigate();
  const reports = useDoctorReports({ lifecycle_status: 'hitl_required' });

  if (reports.isError) {
    return <RetryPanel onRetry={() => void reports.refetch()} message={normalizeApiError(reports.error).message} />;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-clinical-text-primary">HITL Queue</h1>
          <p className="mt-1 text-sm text-clinical-text-secondary">Reports that need doctor verification.</p>
        </div>
      </div>

      {reports.isLoading ? (
        <Skeleton variant="card" rows={5} />
      ) : (reports.data ?? []).length === 0 ? (
        <EmptyState title="No reports currently need HITL review" />
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
      )}
    </div>
  );
}
