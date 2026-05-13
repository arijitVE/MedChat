import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { AlertTriangle, ArrowLeft } from 'lucide-react';
import { RetryPanel } from '../../components/feedback/RetryPanel';
import { FieldsTable } from '../../components/report/FieldsTable';
import { ReportStatusBadge } from '../../components/report/ReportStatusBadge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Skeleton } from '../../components/ui/Skeleton';
import { useAdminReportDetail, useOpenAdminRawReport } from '../../hooks/useReports';
import { useAdminEditField, useAdminUnlockReport, useAdminVerifyReport } from '../../hooks/useVerification';
import { normalizeApiError } from '../../lib/apiError';
import { getReportDisplayName } from '../../lib/reportName';
import type { ReportField } from '../../types/report';

export default function AdminReportDetailPage() {
  const { reportId = '' } = useParams();
  const navigate = useNavigate();
  const [message, setMessage] = useState<string | null>(null);
  const [editingFieldName, setEditingFieldName] = useState<string | null>(null);
  const report = useAdminReportDetail(reportId);
  const rawReport = useOpenAdminRawReport();
  const verifyReport = useAdminVerifyReport();
  const unlockReport = useAdminUnlockReport();
  const editField = useAdminEditField();

  const handleEditField = (_reportId: string, field: ReportField, value: string) => {
    setMessage(null);
    setEditingFieldName(field.field_name);
    editField.mutate(
      {
        reportId,
        fieldName: field.field_name,
        data: {
          edited_value: value,
          edit_reason: 'Admin corrected extracted value',
        },
      },
      {
        onSuccess: () => {
          setMessage(`${field.field_name} updated. Verify the report when review is complete.`);
        },
        onError: (error) => {
          setMessage(normalizeApiError(error).message);
        },
        onSettled: () => setEditingFieldName(null),
      },
    );
  };

  if (report.isError) {
    return <RetryPanel onRetry={() => void report.refetch()} message={normalizeApiError(report.error).message} />;
  }

  const reportData = report.data?.report;
  const fields = report.data?.fields ?? [];
  const hasFinalField = fields.some((field) => field.is_final);
  const abnormalFields = fields.filter((field) => field.is_abnormal);
  const reportLocked =
    hasFinalField ||
    reportData?.lifecycle_status === 'doctor_verified' ||
    reportData?.lifecycle_status === 'fully_verified' ||
    reportData?.lifecycle_status === 'verified' ||
    reportData?.lifecycle_status === 'released';

  const assignedDoctorName = reportData?.assigned_doctor_name ?? reportData?.doctor_name;
  const assignedDoctorId = reportData?.assigned_doctor_id ?? reportData?.doctor_id;

  return (
    <div className="space-y-6">
      <div>
        <Button variant="ghost" className="min-h-8 px-2" onClick={() => navigate('/admin/reports')}>
          <ArrowLeft className="mr-2 h-4 w-4" aria-hidden="true" />
          Back to Reports
        </Button>
      </div>

      <Card>
        {report.isLoading || !reportData ? (
          <Skeleton variant="text" rows={3} />
        ) : (
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 className="text-lg font-semibold text-clinical-text-primary">
                {getReportDisplayName(reportData)}
              </h1>
              <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-clinical-text-secondary">
                <ReportStatusBadge status={reportData.lifecycle_status} />
                <span>{reportData.inferred_document_type}</span>
                <span>Uploaded {new Date(reportData.first_uploaded_at).toLocaleDateString()}</span>
                <span>{fields.length} extracted fields</span>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="secondary"
                loading={rawReport.isPending}
                onClick={() => rawReport.mutate(reportData.report_id)}
              >
                Open Original File
              </Button>
              {reportLocked ? (
                <Button
                  variant="secondary"
                  loading={unlockReport.isPending}
                  onClick={() => {
                    setMessage(null);
                    unlockReport.mutate(reportData.report_id, {
                      onSuccess: () => setMessage('Report unlocked. You can edit fields and verify again.'),
                      onError: (error) => setMessage(normalizeApiError(error).message),
                    });
                  }}
                >
                  Unlock Report
                </Button>
              ) : (
                <Button
                  loading={verifyReport.isPending}
                  disabled={fields.length === 0}
                  onClick={() => {
                    setMessage(null);
                    verifyReport.mutate(reportData.report_id, {
                      onSuccess: (result) => setMessage(`Report verified. ${result.verified_fields} fields locked.`),
                      onError: (error) => setMessage(normalizeApiError(error).message),
                    });
                  }}
                >
                  Verify Report
                </Button>
              )}
            </div>
          </div>
        )}
      </Card>

      {message ? (
        <div className="rounded-md border border-clinical-border bg-clinical-surface px-4 py-3 text-sm text-clinical-text-secondary" role="status">
          {message}
        </div>
      ) : null}

      {reportData?.is_duplicate ? (
        <div
          className="flex items-center gap-2 rounded-lg border border-clinical-warning bg-clinical-hitl-bg px-4 py-3 text-sm text-clinical-hitl"
          role="status"
        >
          <AlertTriangle className="h-4 w-4" aria-hidden="true" />
          Flagged as probable duplicate
        </div>
      ) : null}

      <div className="grid gap-6">
        <Card>
          <h2 className="text-base font-semibold text-clinical-text-primary">Report Ownership</h2>
          {report.isLoading || !reportData ? (
            <Skeleton variant="text" rows={2} />
          ) : (
            <div className="mt-3 grid gap-3 text-sm md:grid-cols-2">
              <div>
                <p className="text-clinical-text-secondary">Patient</p>
                <p className="font-semibold">{reportData.patient_name ?? 'Unknown patient'}</p>
                <p className="mt-1 font-mono text-xs text-clinical-text-muted">
                  {reportData.patient_uid ?? reportData.patient_id}
                </p>
              </div>
              <div>
                <p className="text-clinical-text-secondary">Assigned doctor</p>
                <p className="font-semibold">{assignedDoctorName ?? 'No active doctor assigned'}</p>
                <p className="mt-1 font-mono text-xs text-clinical-text-muted">{assignedDoctorId ?? '-'}</p>
              </div>
            </div>
          )}
        </Card>

        <Card>
          <h2 className="text-base font-semibold text-clinical-text-primary">Clinical Review Snapshot</h2>
          <div className="mt-3 grid gap-3 text-sm md:grid-cols-3">
            <div>
              <p className="text-clinical-text-secondary">AI confidence average</p>
              <p className="font-semibold">
                {fields.length > 0
                  ? `${Math.round((fields.reduce((sum, field) => sum + field.confidence, 0) / fields.length) * 100)}%`
                  : '-'}
              </p>
            </div>
            <div>
              <p className="text-clinical-text-secondary">Abnormal fields</p>
              <p className="font-semibold">{abnormalFields.length}</p>
            </div>
            <div>
              <p className="text-clinical-text-secondary">Verification status</p>
              <p className="font-semibold">{reportLocked ? 'Verified and locked' : 'Editable review'}</p>
            </div>
          </div>
        </Card>

        {rawReport.isError ? (
          <RetryPanel onRetry={() => rawReport.reset()} message={normalizeApiError(rawReport.error).message} />
        ) : null}

        <FieldsTable
          fields={fields}
          reportId={reportId}
          role="admin"
          isLoading={report.isLoading}
          reportLocked={reportLocked}
          editingFieldName={editingFieldName}
          onEditField={handleEditField}
        />
      </div>
    </div>
  );
}
