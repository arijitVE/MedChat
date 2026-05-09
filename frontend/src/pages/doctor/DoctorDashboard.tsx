import { Link } from 'react-router-dom';
import { Card } from '../../components/ui/Card';
import { Skeleton } from '../../components/ui/Skeleton';
import { RetryPanel } from '../../components/feedback/RetryPanel';
import { ReportStatusBadge } from '../../components/report/ReportStatusBadge';
import { useDoctorDashboard } from '../../hooks/useReports';
import { normalizeApiError } from '../../lib/apiError';
import { sanitizeFilename } from '../../lib/sanitize';

export default function DoctorDashboard() {
  const dashboard = useDoctorDashboard();

  if (dashboard.isError) {
    return (
      <RetryPanel
        onRetry={() => void dashboard.refetch()}
        message={normalizeApiError(dashboard.error).message}
      />
    );
  }

  const data = dashboard.data;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-clinical-text-primary">Doctor Dashboard</h1>
        <p className="mt-1 text-sm text-clinical-text-secondary">Recent clinical activity</p>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        {dashboard.isLoading ? (
          <Skeleton variant="stat" rows={4} className="md:col-span-4 md:grid md:grid-cols-4 md:gap-4 md:space-y-0" />
        ) : (
          <>
            <Card>
              <p className="text-sm text-clinical-text-secondary">Patients</p>
              <p className="mt-2 text-2xl font-semibold">{data?.patient_count ?? 0}</p>
            </Card>
            <Card>
              <p className="text-sm text-clinical-text-secondary">HITL Pending</p>
              <p className="mt-2 text-2xl font-semibold">{data?.hitl_count ?? 0}</p>
            </Card>
            <Card>
              <p className="text-sm text-clinical-text-secondary">Recent Uploads</p>
              <p className="mt-2 text-2xl font-semibold">{data?.recent_uploads.length ?? 0}</p>
            </Card>
            <Card>
              <p className="text-sm text-clinical-text-secondary">Processing</p>
              <p className="mt-2 text-2xl font-semibold">
                {data?.recent_uploads.filter((report) => report.lifecycle_status === 'processing').length ?? 0}
              </p>
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
        {dashboard.isLoading ? (
          <Skeleton variant="table-row" rows={8} />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-clinical-text-secondary">
                <tr>
                  <th scope="col" className="py-2 font-medium">File</th>
                  <th scope="col" className="py-2 font-medium">Document Type</th>
                  <th scope="col" className="py-2 font-medium">Status</th>
                  <th scope="col" className="py-2 font-medium">Uploaded</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-clinical-border">
                {(data?.recent_uploads ?? []).slice(0, 8).map((report) => (
                  <tr key={report.report_id}>
                    <td className="py-3">
                      <Link className="font-medium text-clinical-primary hover:underline" to={`/doctor/reports/${report.report_id}`}>
                        {sanitizeFilename(report.file_name)}
                      </Link>
                    </td>
                    <td className="py-3 text-clinical-text-secondary">{report.inferred_document_type}</td>
                    <td className="py-3"><ReportStatusBadge status={report.lifecycle_status} /></td>
                    <td className="py-3 text-clinical-text-secondary">
                      {new Date(report.first_uploaded_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
