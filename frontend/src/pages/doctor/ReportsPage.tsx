import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { RetryPanel } from '../../components/feedback/RetryPanel';
import { ReportCard } from '../../components/report/ReportCard';
import { Card } from '../../components/ui/Card';
import { EmptyState } from '../../components/ui/EmptyState';
import { Skeleton } from '../../components/ui/Skeleton';
import { useDoctorReports } from '../../hooks/useReports';
import { normalizeApiError } from '../../lib/apiError';

const statusOptions = [
  '',
  'uploaded',
  'processing',
  'auto_approved',
  'hitl_required',
  'doctor_verified',
  'fully_verified',
  'failed',
];

export default function ReportsPage() {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('');
  const reports = useDoctorReports({
    query: query.trim() || undefined,
    lifecycle_status: status || undefined,
  });

  if (reports.isError) {
    return <RetryPanel onRetry={() => void reports.refetch()} message={normalizeApiError(reports.error).message} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-clinical-text-primary">Reports</h1>
        <p className="mt-1 text-sm text-clinical-text-secondary">Assigned and uploaded reports for clinical review.</p>
      </div>

      <Card>
        <div className="grid gap-3 md:grid-cols-[1fr_220px]">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search report name or type"
            className="rounded-md border border-clinical-border px-3 py-2 text-sm outline-none focus:border-clinical-primary focus:ring-2 focus:ring-clinical-primary-light"
          />
          <select
            value={status}
            onChange={(event) => setStatus(event.target.value)}
            className="rounded-md border border-clinical-border bg-clinical-surface px-3 py-2 text-sm outline-none focus:border-clinical-primary focus:ring-2 focus:ring-clinical-primary-light"
          >
            {statusOptions.map((option) => (
              <option key={option || 'all'} value={option}>
                {option ? option.replaceAll('_', ' ') : 'All statuses'}
              </option>
            ))}
          </select>
        </div>
      </Card>

      {reports.isLoading ? (
        <Skeleton variant="card" rows={5} />
      ) : (reports.data ?? []).length === 0 ? (
        <EmptyState title="No reports found" />
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
