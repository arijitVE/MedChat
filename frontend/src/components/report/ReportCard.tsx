import { FileText } from 'lucide-react';
import { Card } from '../ui/Card';
import { getReportDisplayName } from '../../lib/reportName';
import type { Report } from '../../types/report';
import { ReportStatusBadge } from './ReportStatusBadge';

interface ReportCardProps {
  report: Report;
  onSelect?: (report: Report) => void;
  className?: string;
}

export function ReportCard({ report, onSelect, className = '' }: ReportCardProps) {
  const content = (
    <Card className={`flex min-h-24 items-start gap-4 p-4 ${className}`}>
      <div className="rounded-md bg-clinical-primary-light p-2 text-clinical-primary">
        <FileText className="h-5 w-5" aria-hidden="true" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="truncate text-sm font-semibold text-clinical-text-primary">
              {getReportDisplayName(report)}
            </h3>
            <p className="mt-1 text-xs text-clinical-text-secondary">
              {report.inferred_document_type === 'unknown'
                ? 'Processing'
                : report.inferred_document_type}
            </p>
          </div>
          <ReportStatusBadge status={report.lifecycle_status} />
        </div>
        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-clinical-text-muted">
          <span>Uploaded {new Date(report.first_uploaded_at).toLocaleDateString()}</span>
          <span>Uploads {report.upload_count}</span>
          {report.is_duplicate ? <span className="text-clinical-warning">Probable duplicate</span> : null}
        </div>
      </div>
    </Card>
  );

  if (!onSelect) {
    return content;
  }

  return (
    <button
      type="button"
      className="block w-full rounded-lg text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-clinical-primary"
      onClick={() => onSelect(report)}
    >
      {content}
    </button>
  );
}
