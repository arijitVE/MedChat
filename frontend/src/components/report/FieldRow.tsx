import { CheckCircle2, Lock, PencilLine } from 'lucide-react';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import type { ReportField } from '../../types/report';

interface FieldRowProps {
  field: ReportField;
  reportId: string;
  role: 'doctor' | 'patient';
  onVerifyField?: (reportId: string, field: ReportField) => void;
}

function getFieldStatus(field: ReportField) {
  if (field.is_final) {
    return { label: 'Doctor verified', variant: 'final' as const, icon: Lock };
  }
  if (field.patient_verified && !field.doctor_verified) {
    return { label: 'Patient verified', variant: 'verified' as const, icon: CheckCircle2 };
  }
  if (field.pipeline_status === 'hitl' && !field.doctor_verified) {
    return { label: 'Needs verification', variant: 'hitl' as const, icon: PencilLine };
  }
  return { label: 'Auto-approved', variant: 'auto' as const, icon: CheckCircle2 };
}

function canVerifyField(field: ReportField, role: 'doctor' | 'patient'): boolean {
  if (field.is_final) {
    return false;
  }
  if (role === 'doctor') {
    return field.pipeline_status === 'hitl' || field.patient_verified;
  }
  return field.pipeline_status === 'hitl' && !field.patient_verified;
}

export function FieldRow({ field, reportId, role, onVerifyField }: FieldRowProps) {
  const status = getFieldStatus(field);
  const StatusIcon = status.icon;
  const canVerify = canVerifyField(field, role);

  return (
    <tr className="hover:bg-slate-50">
      <td className="px-4 py-3 text-sm font-medium text-clinical-text-primary">
        {field.field_name}
      </td>
      <td className="px-4 py-3 text-sm text-clinical-text-primary">
        {field.display_value}
      </td>
      <td className="px-4 py-3 text-sm text-clinical-text-secondary">
        {field.reference_range ?? '-'}
      </td>
      <td className="px-4 py-3 text-sm text-clinical-text-secondary">
        {Math.round(field.confidence * 100)}%
      </td>
      <td className="px-4 py-3">
        <Badge variant={status.variant} role="status" aria-label={`Field status: ${status.label}`}>
          <StatusIcon className="mr-1 h-3 w-3" aria-hidden="true" />
          {status.label}
        </Badge>
      </td>
      <td className="px-4 py-3 text-right">
        {canVerify && onVerifyField ? (
          <Button variant="secondary" className="min-h-8 px-3 py-1" onClick={() => onVerifyField(reportId, field)}>
            Verify
          </Button>
        ) : (
          <span className="text-xs text-clinical-text-muted">
            {field.is_final ? 'Final' : 'No action'}
          </span>
        )}
      </td>
    </tr>
  );
}
