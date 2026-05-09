import { useParams } from 'react-router-dom';
import { AlertTriangle } from 'lucide-react';
import { RetryPanel } from '../../components/feedback/RetryPanel';
import { FieldsTable } from '../../components/report/FieldsTable';
import { FileViewer } from '../../components/report/FileViewer';
import { ReportStatusBadge } from '../../components/report/ReportStatusBadge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Skeleton } from '../../components/ui/Skeleton';
import { useReleaseToPatient, useReportDetail, useReportFields } from '../../hooks/useReports';
import { useVerifyField } from '../../hooks/useVerification';
import { normalizeApiError } from '../../lib/apiError';
import { sanitizeFilename } from '../../lib/sanitize';
import type { ReportField } from '../../types/report';

export default function ReportDetailPage() {
  const { reportId = '' } = useParams();
  const report = useReportDetail(reportId);
  const fields = useReportFields(reportId);
  const verifyField = useVerifyField();
  const release = useReleaseToPatient();

  const handleVerifyField = (_reportId: string, field: ReportField) => {
    verifyField.mutate({
      reportId,
      fieldName: field.field_name,
      data: { verification_type: 'approved' },
    });
  };

  if (report.isError) {
    return <RetryPanel onRetry={() => void report.refetch()} message={normalizeApiError(report.error).message} />;
  }

  const reportData = report.data;
  const hasFinalField = (fields.data ?? []).some((field) => field.is_final);

  return (
    <div className="space-y-6">
      <Card>
        {report.isLoading || !reportData ? (
          <Skeleton variant="text" rows={3} />
        ) : (
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 className="text-lg font-semibold text-clinical-text-primary">
                {sanitizeFilename(reportData.file_name)}
              </h1>
              <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-clinical-text-secondary">
                <ReportStatusBadge status={reportData.lifecycle_status} />
                <span>{reportData.inferred_document_type}</span>
                <span>Uploaded {new Date(reportData.first_uploaded_at).toLocaleDateString()}</span>
              </div>
            </div>
            <div className="flex gap-2">
              {!hasFinalField ? (
                <Button variant="secondary" disabled>
                  Re-upload
                </Button>
              ) : null}
              <Button
                loading={release.isPending}
                disabled={reportData.released_to_patient}
                onClick={() => release.mutate(reportData.report_id)}
              >
                Release
              </Button>
            </div>
          </div>
        )}
      </Card>

      {reportData?.is_duplicate ? (
        <div
          className="flex items-center gap-2 rounded-lg border border-clinical-warning bg-clinical-hitl-bg px-4 py-3 text-sm text-clinical-hitl"
          role="status"
        >
          <AlertTriangle className="h-4 w-4" aria-hidden="true" />
          Flagged as probable duplicate
        </div>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,3fr)_minmax(360px,2fr)]">
        {fields.isError ? (
          <RetryPanel onRetry={() => void fields.refetch()} message={normalizeApiError(fields.error).message} />
        ) : (
          <FieldsTable
            fields={fields.data ?? []}
            reportId={reportId}
            role="doctor"
            isLoading={fields.isLoading}
            onVerifyField={handleVerifyField}
          />
        )}
        {reportData ? (
          <FileViewer reportId={reportId} role="doctor" mimeType={reportData.file_mime} />
        ) : (
          <Skeleton variant="file" />
        )}
      </div>
    </div>
  );
}
