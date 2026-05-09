import { AlertTriangle, CheckCircle2 } from 'lucide-react';
import { Card } from '../ui/Card';
import { Skeleton } from '../ui/Skeleton';
import type { ClinicalField } from '../../types/intelligence';

interface AbnormalityPanelProps {
  abnormalFields: ClinicalField[];
  normalFields: ClinicalField[];
  isLoading?: boolean;
  className?: string;
}

function formatFieldValue(field: ClinicalField): string {
  return [field.value, field.unit].filter(Boolean).join(' ');
}

export function AbnormalityPanel({
  abnormalFields,
  normalFields,
  isLoading = false,
  className = '',
}: AbnormalityPanelProps) {
  if (isLoading) {
    return <Skeleton variant="card" rows={2} className={className} />;
  }

  return (
    <Card className={className}>
      <div className="grid gap-4 md:grid-cols-2">
        <section aria-label="Abnormal fields">
          <div className="mb-3 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-clinical-critical" aria-hidden="true" />
            <h3 className="text-sm font-semibold text-clinical-text-primary">
              Abnormal ({abnormalFields.length})
            </h3>
          </div>
          <div className="space-y-2">
            {abnormalFields.length === 0 ? (
              <p className="text-sm text-clinical-text-secondary">No abnormal fields.</p>
            ) : (
              abnormalFields.map((field) => (
                <div
                  key={field.field_id}
                  className="rounded-md border border-clinical-critical bg-clinical-critical-bg px-3 py-2"
                >
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="mt-0.5 h-4 w-4 text-clinical-critical" aria-hidden="true" />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-clinical-text-primary">{field.name}</p>
                      <p className="text-sm text-clinical-text-secondary">
                        {formatFieldValue(field)}
                      </p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        <section aria-label="Normal fields">
          <div className="mb-3 flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-clinical-auto" aria-hidden="true" />
            <h3 className="text-sm font-semibold text-clinical-text-primary">
              Normal ({normalFields.length})
            </h3>
          </div>
          <div className="space-y-2">
            {normalFields.length === 0 ? (
              <p className="text-sm text-clinical-text-secondary">No normal fields.</p>
            ) : (
              normalFields.map((field) => (
                <div
                  key={field.field_id}
                  className="rounded-md border border-clinical-auto bg-clinical-auto-bg px-3 py-2"
                >
                  <div className="flex items-start gap-2">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 text-clinical-auto" aria-hidden="true" />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-clinical-text-primary">{field.name}</p>
                      <p className="text-sm text-clinical-text-secondary">
                        {formatFieldValue(field)}
                      </p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </Card>
  );
}
