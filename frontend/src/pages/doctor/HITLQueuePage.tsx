import { useState } from 'react';
import { Link } from 'react-router-dom';
import { EmptyState } from '../../components/ui/EmptyState';
import { Skeleton } from '../../components/ui/Skeleton';
import { RetryPanel } from '../../components/feedback/RetryPanel';
import { useDoctorHITLQueue } from '../../hooks/useReports';
import { normalizeApiError } from '../../lib/apiError';
import { sanitizeFilename } from '../../lib/sanitize';

export default function HITLQueuePage() {
  const [myPatientsOnly, setMyPatientsOnly] = useState(false);
  const queue = useDoctorHITLQueue(myPatientsOnly);

  if (queue.isError) {
    return <RetryPanel onRetry={() => void queue.refetch()} message={normalizeApiError(queue.error).message} />;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-clinical-text-primary">HITL Queue</h1>
          <p className="mt-1 text-sm text-clinical-text-secondary">Reports that need doctor verification.</p>
        </div>
        <div className="rounded-md border border-clinical-border bg-clinical-surface p-1">
          <button
            type="button"
            className={`rounded px-3 py-1.5 text-sm ${!myPatientsOnly ? 'bg-clinical-primary text-white' : 'text-clinical-text-secondary'}`}
            onClick={() => setMyPatientsOnly(false)}
          >
            All Patients
          </button>
          <button
            type="button"
            className={`rounded px-3 py-1.5 text-sm ${myPatientsOnly ? 'bg-clinical-primary text-white' : 'text-clinical-text-secondary'}`}
            onClick={() => setMyPatientsOnly(true)}
          >
            My Patients Only
          </button>
        </div>
      </div>

      {queue.isLoading ? (
        <Skeleton variant="table-row" rows={8} />
      ) : (queue.data ?? []).length === 0 ? (
        <EmptyState title="No reports waiting for verification" />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-clinical-border bg-clinical-surface">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-clinical-text-secondary">
              <tr>
                <th scope="col" className="px-4 py-3">Report</th>
                <th scope="col" className="px-4 py-3">Patient</th>
                <th scope="col" className="px-4 py-3">Fields Pending</th>
                <th scope="col" className="px-4 py-3">Uploaded</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-clinical-border">
              {(queue.data ?? []).map((item) => (
                <tr key={item.report_id}>
                  <td className="px-4 py-3">
                    <Link className="font-medium text-clinical-primary hover:underline" to={`/doctor/reports/${item.report_id}`}>
                      {sanitizeFilename(item.file_name)}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-clinical-text-secondary">{item.patient_id}</td>
                  <td className="px-4 py-3 text-clinical-text-secondary">{item.hitl_count}</td>
                  <td className="px-4 py-3 text-clinical-text-secondary">
                    {new Date(item.first_uploaded_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
