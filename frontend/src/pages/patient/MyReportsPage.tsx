import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { DuplicateWarningModal } from '../../components/report/DuplicateWarningModal';
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
import type { ApiError } from '../../lib/apiError';
import type { DuplicateWarning, ExactDuplicateError, Report } from '../../types/report';

const pageSize = 8;

const documentTypeLabels: Record<string, string> = {
  unknown: 'Processing',
  cbc: 'Complete Blood Count',
  lipid: 'Lipid Panel',
  thyroid: 'Thyroid Panel',
  metabolic: 'Metabolic Panel',
};

type DuplicateState = {
  type: 'exact' | 'probable';
  existingReportId: string;
  existingUploadedAt: string;
  uploadedByRole: 'doctor' | 'patient';
};

function duplicateFromError(error: ApiError): DuplicateState | null {
  const raw = error.raw as Partial<ExactDuplicateError> | undefined;
  if (!raw?.existing_report_id || !raw.existing_uploaded_at || !raw.uploaded_by_role) {
    return null;
  }
  return {
    type: 'exact',
    existingReportId: raw.existing_report_id,
    existingUploadedAt: raw.existing_uploaded_at,
    uploadedByRole: raw.uploaded_by_role,
  };
}

function duplicateFromWarning(warning: DuplicateWarning): DuplicateState {
  return {
    type: 'probable',
    existingReportId: warning.existing_report_id,
    existingUploadedAt: warning.existing_uploaded_at,
    uploadedByRole: warning.uploaded_by_role,
  };
}

export default function MyReportsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [documentType, setDocumentType] = useState('');
  const [page, setPage] = useState(1);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [duplicate, setDuplicate] = useState<DuplicateState | null>(null);
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

  const uploadFile = async (file: File, force = false): Promise<Report> => {
    const formData = new FormData();
    formData.append('file', file);
    const report = await upload.mutateAsync({ formData, force });
    if (report.duplicate_warning) {
      setDuplicate(duplicateFromWarning(report.duplicate_warning));
    } else {
      navigate(`/patient/reports/${report.report_id}`);
    }
    return report;
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
        onFileSelected={setSelectedFile}
        onUpload={(file) => uploadFile(file)}
        onDuplicate={(error) => setDuplicate(duplicateFromError(error))}
        onError={(error) => {
          const apiError = normalizeApiError(error);
          setErrorMessage(
            apiError.statusCode === 429
              ? 'Upload rate limit reached - try again later'
              : apiError.message,
          );
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

      {duplicate ? (
        <DuplicateWarningModal
          type={duplicate.type}
          existingReportId={duplicate.existingReportId}
          existingUploadedAt={duplicate.existingUploadedAt}
          uploadedByRole={duplicate.uploadedByRole}
          onUseExisting={() => navigate(`/patient/reports/${duplicate.existingReportId}`)}
          onForceUpload={() => {
            if (selectedFile) {
              setDuplicate(null);
              void uploadFile(selectedFile, true);
            }
          }}
          onDismiss={duplicate.type === 'probable' ? () => setDuplicate(null) : undefined}
        />
      ) : null}
    </div>
  );
}
