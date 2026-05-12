import { useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { Lock } from 'lucide-react';
import { ReportStatusBadge } from '../../components/report/ReportStatusBadge';
import { Badge } from '../../components/ui/Badge';
import { Card } from '../../components/ui/Card';
import { Skeleton } from '../../components/ui/Skeleton';
import { RetryPanel } from '../../components/feedback/RetryPanel';
import { useMyReport } from '../../hooks/useReports';
import { useMyEDA } from '../../hooks/useIntelligence';
import { normalizeApiError } from '../../lib/apiError';
import { getReportDisplayName } from '../../lib/reportName';
import type { Report, ReportField } from '../../types/report';

type PatientReportDetail = {
  report: Report;
  fields: ReportField[];
};

function FieldCard({ field }: { field: ReportField }) {
  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-clinical-text-primary">{field.field_name}</h3>
          <p className="mt-1 text-base text-clinical-text-primary">{field.display_value}</p>
          <dl className="mt-2 grid gap-1 text-xs text-clinical-text-secondary sm:grid-cols-3">
            <div>
              <dt>Unit</dt>
              <dd className="font-medium text-clinical-text-primary">{field.unit ?? '-'}</dd>
            </div>
            <div>
              <dt>Reference</dt>
              <dd className="font-medium text-clinical-text-primary">{field.reference_range ?? '-'}</dd>
            </div>
            <div>
              <dt>Confidence</dt>
              <dd className="font-medium text-clinical-text-primary">{Math.round(field.confidence * 100)}%</dd>
            </div>
          </dl>
        </div>
        {field.is_final || field.doctor_verified ? (
          <Badge variant="final" role="status" aria-label="Doctor verified">
            <Lock className="mr-1 h-3 w-3" aria-hidden="true" />
            Doctor verified
          </Badge>
        ) : field.pipeline_status === 'hitl' ? (
          <Badge variant="hitl" role="status">Doctor review pending</Badge>
        ) : (
          <Badge variant="auto" role="status">Auto-approved</Badge>
        )}
      </div>
    </Card>
  );
}

export default function ReportViewPage() {
  const { reportId = '' } = useParams();
  const report = useMyReport(reportId);
  const reportDetail = report.data as unknown as PatientReportDetail | undefined;
  const reportData = reportDetail?.report;
  const fieldsFromDetail = useMemo(() => reportDetail?.fields ?? [], [reportDetail]);
  const shouldLoadEda = Boolean(
    reportData &&
      reportData.lifecycle_status !== 'uploaded' &&
      reportData.lifecycle_status !== 'processing' &&
      reportData.lifecycle_status !== 'failed',
  );
  const eda = useMyEDA(reportId, shouldLoadEda);
  const averageConfidence = useMemo(() => {
    if (fieldsFromDetail.length === 0) {
      return null;
    }
    const total = fieldsFromDetail.reduce((sum, field) => sum + field.confidence, 0);
    return Math.round((total / fieldsFromDetail.length) * 100);
  }, [fieldsFromDetail]);

  if (report.isError) {
    return <RetryPanel onRetry={() => void report.refetch()} message={normalizeApiError(report.error).message} />;
  }

  if (!reportData && !report.isLoading && !report.isError) {
    return <RetryPanel message="Report not found" onRetry={() => void report.refetch()} />;
  }

  const edaFields = eda.data?.chart_json.data.fields ?? [];
  const edaValues = eda.data?.chart_json.data.values ?? [];

  return (
    <div className="space-y-6">
      <Card>
        {report.isLoading || !reportData ? (
          <Skeleton variant="text" rows={3} />
        ) : (
          <div>
            <h1 className="text-lg font-semibold text-clinical-text-primary">
              {getReportDisplayName(reportData)}
            </h1>
            <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-clinical-text-secondary">
              <ReportStatusBadge status={reportData.lifecycle_status} />
              <span>{reportData.inferred_document_type === 'unknown' ? 'Processing' : reportData.inferred_document_type}</span>
              <span>Uploaded {new Date(reportData.first_uploaded_at).toLocaleDateString()}</span>
              <span>Confidence {averageConfidence ?? '-'}%</span>
            </div>
          </div>
        )}
      </Card>

      {reportData?.lifecycle_status === 'failed' ? (
        <Card className="border-clinical-critical bg-clinical-critical-bg">
          <h2 className="text-base font-semibold text-clinical-critical">Processing failed</h2>
          <p className="mt-2 text-sm text-clinical-critical">
            Report processing failed. Please try again or upload a clearer document.
          </p>
        </Card>
      ) : null}

      <Card>
        <h2 className="text-base font-semibold text-clinical-text-primary">AI Summary</h2>
        <p className="mt-2 text-sm leading-6 text-clinical-text-secondary">
          This page shows the values extracted from your report in patient-friendly form. It is educational and does not replace medical advice from your doctor.
        </p>
      </Card>

      <section className="grid gap-3">
        <h2 className="text-base font-semibold text-clinical-text-primary">Extracted Fields</h2>
        {report.isLoading ? (
          <Skeleton variant="card" rows={6} />
        ) : fieldsFromDetail.length === 0 ? (
          <Card>
            <p className="text-sm text-clinical-text-secondary">Extracted fields are not available yet.</p>
          </Card>
        ) : (
          fieldsFromDetail.map((field) => (
            <FieldCard key={field.field_name} field={field} />
          ))
        )}
      </section>

      {edaFields.length > 0 ? (
        <Card>
          <h2 className="text-base font-semibold text-clinical-text-primary">EDA & Insights</h2>
          <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
            {edaFields.map((field, index) => (
              <div key={`${field}-${index}`} className="rounded-md border border-clinical-border px-3 py-2">
                <dt className="font-medium text-clinical-text-primary">{field}</dt>
                <dd className="mt-1 text-clinical-text-secondary">{edaValues[index] ?? '-'}</dd>
              </div>
            ))}
          </dl>
        </Card>
      ) : null}

      <Card>
        <h2 className="text-base font-semibold text-clinical-text-primary">Verification Information</h2>
        <p className="mt-2 text-sm text-clinical-text-secondary">
          Auto-approved values met system confidence checks. Doctor verified values were reviewed by a clinician. Items marked doctor review pending are still being reviewed.
        </p>
      </Card>
    </div>
  );
}
