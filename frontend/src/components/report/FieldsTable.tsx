import { FieldRow } from './FieldRow';
import { Skeleton } from '../ui/Skeleton';
import type { ReportField } from '../../types/report';

interface FieldsTableProps {
  fields: ReportField[];
  reportId: string;
  role: 'doctor' | 'patient';
  isLoading?: boolean;
  onVerifyField?: (reportId: string, field: ReportField) => void;
  className?: string;
}

export function FieldsTable({
  fields,
  reportId,
  role,
  isLoading = false,
  onVerifyField,
  className = '',
}: FieldsTableProps) {
  return (
    <div className={`overflow-x-auto rounded-lg border border-clinical-border bg-clinical-surface ${className}`}>
      <table className="w-full text-left text-sm">
        <thead className="bg-slate-50 text-clinical-text-secondary">
          <tr>
            <th scope="col" className="px-4 py-3 text-xs font-semibold uppercase tracking-normal">
              Field
            </th>
            <th scope="col" className="px-4 py-3 text-xs font-semibold uppercase tracking-normal">
              Value
            </th>
            <th scope="col" className="px-4 py-3 text-xs font-semibold uppercase tracking-normal">
              Reference
            </th>
            <th scope="col" aria-sort="none" className="px-4 py-3 text-xs font-semibold uppercase tracking-normal">
              Confidence
            </th>
            <th scope="col" className="px-4 py-3 text-xs font-semibold uppercase tracking-normal">
              Status
            </th>
            <th scope="col" className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-normal">
              Action
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-clinical-border">
          {isLoading ? (
            <tr>
              <td colSpan={6} className="px-4 py-3">
                <Skeleton variant="table-row" rows={8} />
              </td>
            </tr>
          ) : (
            fields.map((field) => (
              <FieldRow
                key={field.field_name}
                field={field}
                reportId={reportId}
                role={role}
                onVerifyField={onVerifyField}
              />
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
