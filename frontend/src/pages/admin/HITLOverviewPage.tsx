import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { adminApi } from '../../api/admin';
import { RetryPanel } from '../../components/feedback/RetryPanel';
import { Button } from '../../components/ui/Button';
import { EmptyState } from '../../components/ui/EmptyState';
import { Skeleton } from '../../components/ui/Skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/Table';
import { normalizeApiError } from '../../lib/apiError';
import { queryKeys, staleTime } from '../../lib/queryKeys';

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(new Date(value));
}

export default function HITLOverviewPage() {
  const navigate = useNavigate();
  const queue = useQuery({
    queryKey: queryKeys.admin.hitlQueue,
    queryFn: async () => {
      try {
        const response = await adminApi.getHITLQueue();
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    staleTime: staleTime.hitlQueue,
  });

  const sortedQueue = useMemo(
    () => [...(queue.data ?? [])].sort((a, b) => b.days_waiting - a.days_waiting),
    [queue.data],
  );

  if (queue.isError) {
    return <RetryPanel onRetry={() => void queue.refetch()} message={normalizeApiError(queue.error).message} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-clinical-text-primary">HITL Overview</h1>
        <p className="mt-1 text-sm text-clinical-text-secondary">Read-only view of reports waiting for verification.</p>
      </div>

      {queue.isLoading ? (
        <Skeleton variant="table-row" rows={8} />
      ) : sortedQueue.length === 0 ? (
        <EmptyState title="No HITL reports pending" />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Patient</TableHead>
              <TableHead>Patient UID</TableHead>
              <TableHead>Doctor</TableHead>
              <TableHead>Report Date</TableHead>
              <TableHead>Fields Pending</TableHead>
              <TableHead>Days Waiting</TableHead>
              <TableHead>Report</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedQueue.map((item) => (
              <TableRow key={item.report_id}>
                <TableCell className="font-medium">{item.patient_name}</TableCell>
                <TableCell>{item.patient_uid}</TableCell>
                <TableCell>{item.doctor_name}</TableCell>
                <TableCell>{formatDate(item.report_date)}</TableCell>
                <TableCell>{item.fields_pending}</TableCell>
                <TableCell>{item.days_waiting}</TableCell>
                <TableCell>
                  <Button
                    variant="secondary"
                    className="min-h-8 px-3 py-1"
                    onClick={() => navigate(`/doctor/reports/${item.report_id}`)}
                  >
                    Open
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
