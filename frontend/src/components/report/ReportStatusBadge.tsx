import { Badge } from '../ui/Badge';
import type { LifecycleStatus } from '../../types/report';

interface ReportStatusBadgeProps {
  status: LifecycleStatus;
  className?: string;
}

const statusConfig: Record<LifecycleStatus, { label: string; variant: 'auto' | 'hitl' | 'verified' | 'final' | 'processing' }> = {
  uploaded: { label: 'Uploaded', variant: 'processing' },
  processing: { label: 'Processing', variant: 'processing' },
  auto_approved: { label: 'Auto-approved', variant: 'auto' },
  hitl_required: { label: 'Needs verification', variant: 'hitl' },
  patient_verified: { label: 'Patient verified', variant: 'verified' },
  doctor_verified: { label: 'Doctor verified', variant: 'final' },
  fully_verified: { label: 'Fully verified', variant: 'final' },
  failed: { label: 'Failed', variant: 'hitl' },
};

export function ReportStatusBadge({ status, className = '' }: ReportStatusBadgeProps) {
  const config = statusConfig[status];

  return (
    <Badge
      variant={config.variant}
      className={className}
      role="status"
      aria-label={`Report status: ${config.label}`}
    >
      {config.label}
    </Badge>
  );
}
