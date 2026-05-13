import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { adminApi } from '../../api/admin';
import { Button } from '../../components/ui/Button';
import { Pagination } from '../../components/ui/Pagination';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/Table';
import { queryKeys, staleTime } from '../../lib/queryKeys';
import { sanitizeFilename } from '../../lib/sanitize';
import { PageHeader, QueryState } from './AdminUtils';
import { formatDate } from './adminFormat';

const pageSize = 20;
const statuses = ['', 'uploaded', 'processing', 'auto_approved', 'hitl_required', 'fully_verified', 'failed'];

export default function ReportsPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState('');
  const filters = useMemo(() => ({ page, page_size: pageSize, status: status || undefined }), [page, status]);
  const reports = useQuery({
    queryKey: queryKeys.admin.reports(filters),
    queryFn: async () => (await adminApi.getReports(filters)).data,
    staleTime: staleTime.reportDetail,
  });

  return (
    <div className="space-y-6">
      <PageHeader title="Reports" description="All uploaded reports across patients and doctors." />
      <select
        value={status}
        onChange={(event) => {
          setStatus(event.target.value);
          setPage(1);
        }}
        className="rounded-md border border-clinical-border px-3 py-2 text-sm outline-none focus:border-clinical-primary focus:ring-2 focus:ring-clinical-primary-light"
        aria-label="Filter reports by status"
      >
        {statuses.map((item) => (
          <option key={item || 'all'} value={item}>{item || 'All statuses'}</option>
        ))}
      </select>
      <QueryState
        isLoading={reports.isLoading}
        isError={reports.isError}
        error={reports.error}
        onRetry={() => void reports.refetch()}
        isEmpty={(reports.data?.items ?? []).length === 0}
        emptyTitle="No reports found"
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>File</TableHead>
              <TableHead>Patient</TableHead>
              <TableHead>Doctor</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Released</TableHead>
              <TableHead>Uploaded</TableHead>
              <TableHead className="text-right">Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(reports.data?.items ?? []).map((report) => (
              <TableRow
                key={report.report_id}
                className="cursor-pointer"
                onClick={() => navigate(`/admin/reports/${report.report_id}`)}
              >
                <TableCell className="font-medium">{sanitizeFilename(report.file_name)}</TableCell>
                <TableCell>{report.patient_name ?? report.patient_id}</TableCell>
                <TableCell>{report.doctor_name ?? report.doctor_id ?? '-'}</TableCell>
                <TableCell>{report.lifecycle_status}</TableCell>
                <TableCell>{report.inferred_document_type ?? report.upload_document_type}</TableCell>
                <TableCell>{report.released_to_patient ? 'Yes' : 'No'}</TableCell>
                <TableCell>{formatDate(report.first_uploaded_at)}</TableCell>
                <TableCell className="text-right">
                  <Button
                    variant="secondary"
                    className="min-h-8 px-3 py-1"
                    onClick={(event) => {
                      event.stopPropagation();
                      navigate(`/admin/reports/${report.report_id}`);
                    }}
                  >
                    Open
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </QueryState>
      <Pagination page={reports.data?.page ?? page} totalPages={reports.data?.total_pages ?? 1} onPageChange={setPage} />
    </div>
  );
}
