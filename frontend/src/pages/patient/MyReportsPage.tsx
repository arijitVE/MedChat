import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ReportCard } from '../../components/report/ReportCard';
import { UploadDropzone } from '../../components/report/UploadDropzone';
import { Card } from '../../components/ui/Card';
import { EmptyState } from '../../components/ui/EmptyState';
import { Pagination } from '../../components/ui/Pagination';
import { Skeleton } from '../../components/ui/Skeleton';
import { Toast } from '../../components/ui/Toast';
import { RetryPanel } from '../../components/feedback/RetryPanel';
import { useAuth } from '../../hooks/useAuth';
import { useMyReports, usePatientUploadReport } from '../../hooks/useReports';
import { normalizeApiError } from '../../lib/apiError';
import type { DuplicateWarning, UploadResponse } from '../../types/report';

const pageSize = 8;

const documentTypeLabels: Record<string, string> = {
  unknown: 'Processing',
  cbc: 'Complete Blood Count',
  lipid: 'Lipid Panel',
  thyroid: 'Thyroid Panel',
  metabolic: 'Metabolic Panel',
};

export default function MyReportsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [documentType, setDocumentType] = useState('');
  const [page, setPage] = useState(1);
  const [duplicateWarning, setDuplicateWarning] = useState<DuplicateWarning | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const reports = useMyReports({
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  });
  const upload = usePatientUploadReport();

  const filteredReports = useMemo(() => {
    return (reports.data ?? []).filter((report) =>
      documentType ? report.inferred_document_type === documentType : true,
    );
  }, [documentType, reports.data]);
  const totalPages = Math.max(Math.ceil(filteredReports.length / pageSize), 1);
  const visibleReports = filteredReports.slice((page - 1) * pageSize, page * pageSize);
  const patientUid = user?.patient_uid ?? user?.user_id ?? '';

  const uploadFile = async (file: File): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    setErrorMessage(null);
    setSuccessMessage(null);
    setDuplicateWarning(null);

    const response = await upload.mutateAsync(formData);
    setSuccessMessage('Report uploaded successfully. Processing may take up to 2 minutes.');

    if (response.duplicate_warning) {
      setDuplicateWarning(response.duplicate_warning);
    } else {
      navigate('/patient/reports');
    }

    return response;
  };

  if (reports.isError) {
    return <RetryPanel onRetry={() => void reports.refetch()} message={normalizeApiError(reports.error).message} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-clinical-text-primary">My Reports</h1>
        <p className="mt-1 text-sm text-clinical-text-secondary">Filter and review released medical reports.</p>
      </div>

      {successMessage ? <Toast variant="success">{successMessage}</Toast> : null}
      {duplicateWarning ? (
        <Toast variant="warning" title="Possible duplicate">
          {duplicateWarning.message}
        </Toast>
      ) : null}
      {errorMessage ? <Toast variant="error">{errorMessage}</Toast> : null}

      <Card>
        <div className="grid gap-3 md:grid-cols-3">
          <input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} className="rounded-md border border-clinical-border px-3 py-2 text-sm" aria-label="Date from" />
          <input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} className="rounded-md border border-clinical-border px-3 py-2 text-sm" aria-label="Date to" />
          <select value={documentType} onChange={(event) => { setDocumentType(event.target.value); setPage(1); }} className="rounded-md border border-clinical-border px-3 py-2 text-sm" aria-label="Document type">
            <option value="">All document types</option>
            {Object.entries(documentTypeLabels).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>
      </Card>

      <UploadDropzone
        patientUid={patientUid}
        onUpload={(file) => uploadFile(file)}
        onError={(error) => {
          const apiError = normalizeApiError(error);
          setSuccessMessage(null);
          setDuplicateWarning(null);
          setErrorMessage(apiError.message);
        }}
      />

      {reports.isLoading ? (
        <Skeleton variant="card" rows={4} />
      ) : visibleReports.length === 0 ? (
        <EmptyState title="No reports found" />
      ) : (
        <div className="grid gap-4">
          {visibleReports.map((report) => (
            <ReportCard
              key={report.report_id}
              report={report}
              onSelect={() => navigate(`/patient/reports/${report.report_id}`)}
            />
          ))}
        </div>
      )}

      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />

    </div>
  );
}
