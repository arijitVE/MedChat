import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { CheckCircle2, Lock } from 'lucide-react';
import { FileViewer } from '../../components/report/FileViewer';
import { ReportStatusBadge } from '../../components/report/ReportStatusBadge';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Modal } from '../../components/ui/Modal';
import { Skeleton } from '../../components/ui/Skeleton';
import { RetryPanel } from '../../components/feedback/RetryPanel';
import { useMyReport, useMyReportFields } from '../../hooks/useReports';
import { usePatientVerifyField } from '../../hooks/useVerification';
import { normalizeApiError } from '../../lib/apiError';
import { sanitizeFilename } from '../../lib/sanitize';
import type { ReportField } from '../../types/report';

function FieldCard({
  field,
  reportId,
  onVerify,
}: {
  field: ReportField;
  reportId: string;
  onVerify: (reportId: string, field: ReportField) => void;
}) {
  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-clinical-text-primary">{field.field_name}</h3>
          <p className="mt-1 text-base text-clinical-text-primary">{field.display_value}</p>
          <p className="mt-1 text-xs text-clinical-text-secondary">
            Reference: {field.reference_range ?? '-'}
          </p>
        </div>
        {field.is_final ? (
          <Badge variant="final" role="status" aria-label="Verified by doctor">
            <Lock className="mr-1 h-3 w-3" aria-hidden="true" />
            Verified by doctor
          </Badge>
        ) : field.patient_verified ? (
          <Badge variant="verified" role="status" aria-label="Patient verified">
            <CheckCircle2 className="mr-1 h-3 w-3" aria-hidden="true" />
            Patient verified
          </Badge>
        ) : (
          <Button className="min-h-8 px-3 py-1" variant="secondary" onClick={() => onVerify(reportId, field)}>
            Verify
          </Button>
        )}
      </div>
    </Card>
  );
}

function PatientVerifyModal({
  field,
  isVerifying,
  onClose,
  onConfirm,
}: {
  field: ReportField | null;
  isVerifying: boolean;
  onClose: () => void;
  onConfirm: () => void;
}) {
  return (
    <Modal isOpen={Boolean(field)} title="Verify field" onClose={onClose}>
      {field ? (
        <div className="space-y-4">
          <div className="rounded-md border border-clinical-border bg-clinical-muted p-3">
            <p className="text-sm font-medium text-clinical-text-primary">{field.field_name}</p>
            <p className="mt-1 text-sm text-clinical-text-secondary">{field.display_value}</p>
          </div>
          <p className="text-sm text-clinical-text-secondary">
            Confirm that this value matches your report.
          </p>
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button loading={isVerifying} onClick={onConfirm}>
              Verify
            </Button>
          </div>
        </div>
      ) : null}
    </Modal>
  );
}

export default function ReportViewPage() {
  const { reportId = '' } = useParams();
  const report = useMyReport(reportId);
  const fields = useMyReportFields(reportId);
  const verifyField = usePatientVerifyField();
  const [fieldToVerify, setFieldToVerify] = useState<ReportField | null>(null);

  const handleVerify = (_reportId: string, field: ReportField) => {
    setFieldToVerify(field);
  };

  const confirmVerify = () => {
    if (!fieldToVerify) {
      return;
    }
    verifyField.mutate(
      {
        reportId,
        fieldName: fieldToVerify.field_name,
        data: { verification_type: 'approved' },
      },
      {
        onSuccess: () => setFieldToVerify(null),
      },
    );
  };

  if (report.isError) {
    return <RetryPanel onRetry={() => void report.refetch()} message={normalizeApiError(report.error).message} />;
  }

  const reportData = report.data;

  return (
    <div className="space-y-6">
      <Card>
        {report.isLoading || !reportData ? (
          <Skeleton variant="text" rows={3} />
        ) : (
          <div>
            <h1 className="text-lg font-semibold text-clinical-text-primary">
              {sanitizeFilename(reportData.file_name)}
            </h1>
            <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-clinical-text-secondary">
              <ReportStatusBadge status={reportData.lifecycle_status} />
              <span>{reportData.inferred_document_type === 'unknown' ? 'Processing' : reportData.inferred_document_type}</span>
              <span>Uploaded {new Date(reportData.first_uploaded_at).toLocaleDateString()}</span>
            </div>
          </div>
        )}
      </Card>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(360px,1fr)]">
        {fields.isError ? (
          <RetryPanel onRetry={() => void fields.refetch()} message={normalizeApiError(fields.error).message} />
        ) : fields.isLoading ? (
          <Skeleton variant="card" rows={6} />
        ) : (
          <div className="grid gap-3">
            {(fields.data ?? []).map((field) => (
              <FieldCard key={field.field_name} field={field} reportId={reportId} onVerify={handleVerify} />
            ))}
          </div>
        )}
        {reportData ? (
          <FileViewer reportId={reportId} role="patient" mimeType={reportData.file_mime} />
        ) : (
          <Skeleton variant="file" />
        )}
      </div>
      <PatientVerifyModal
        field={fieldToVerify}
        isVerifying={verifyField.isPending}
        onClose={() => setFieldToVerify(null)}
        onConfirm={confirmVerify}
      />
    </div>
  );
}
