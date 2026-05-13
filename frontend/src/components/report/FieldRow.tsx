import { useState } from 'react';
import { CheckCircle2, Lock, PencilLine } from 'lucide-react';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import type { ReportField } from '../../types/report';

interface FieldRowProps {
  field: ReportField;
  reportId: string;
  role: 'doctor' | 'patient' | 'admin';
  onVerifyField?: (reportId: string, field: ReportField) => void;
  onEditField?: (reportId: string, field: ReportField, value: string) => void;
  reportLocked?: boolean;
  isEditing?: boolean;
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

function canVerifyField(field: ReportField, role: 'doctor' | 'patient' | 'admin'): boolean {
  if (field.is_final) {
    return false;
  }
  if (role === 'doctor' || role === 'admin') {
    return field.pipeline_status === 'hitl' || field.patient_verified;
  }
  return field.pipeline_status === 'hitl' && !field.patient_verified;
}

export function FieldRow({
  field,
  reportId,
  role,
  onVerifyField,
  onEditField,
  reportLocked = false,
  isEditing = false,
}: FieldRowProps) {
  const status = getFieldStatus(field);
  const StatusIcon = status.icon;
  const canVerify = canVerifyField(field, role);
  const [isInlineEditing, setIsInlineEditing] = useState(false);
  const [draftValue, setDraftValue] = useState(field.value ?? field.display_value ?? '');
  const canEdit = (role === 'doctor' || role === 'admin') && !reportLocked && Boolean(onEditField);

  return (
    <tr className="hover:bg-slate-50">
      <td className="px-4 py-3 text-sm font-medium text-clinical-text-primary">
        {field.field_name}
      </td>
      <td className="px-4 py-3 text-sm text-clinical-text-primary">
        {isInlineEditing ? (
          <input
            value={draftValue}
            onChange={(event) => setDraftValue(event.target.value)}
            className="w-full min-w-40 rounded-md border border-clinical-border px-2 py-1 text-sm outline-none focus:border-clinical-primary focus:ring-2 focus:ring-clinical-primary-light"
            aria-label={`Edit ${field.field_name}`}
          />
        ) : (
          field.display_value
        )}
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
        {isInlineEditing ? (
          <div className="flex justify-end gap-2">
            <Button
              className="min-h-8 px-3 py-1"
              loading={isEditing}
              onClick={() => {
                onEditField?.(reportId, field, draftValue);
                setIsInlineEditing(false);
              }}
            >
              Save
            </Button>
            <Button
              variant="ghost"
              className="min-h-8 px-3 py-1"
              onClick={() => {
                setDraftValue(field.value ?? field.display_value ?? '');
                setIsInlineEditing(false);
              }}
            >
              Cancel
            </Button>
          </div>
        ) : canEdit ? (
          <Button
            variant="secondary"
            className="min-h-8 px-3 py-1"
            onClick={() => setIsInlineEditing(true)}
          >
            Edit
          </Button>
        ) : canVerify && onVerifyField ? (
          <Button variant="secondary" className="min-h-8 px-3 py-1" onClick={() => onVerifyField(reportId, field)}>
            Verify
          </Button>
        ) : (
          <span className="text-xs text-clinical-text-muted">
            {reportLocked ? 'Locked' : field.is_final ? 'Final' : 'No action'}
          </span>
        )}
      </td>
    </tr>
  );
}
