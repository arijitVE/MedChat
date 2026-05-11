import { useQuery } from '@tanstack/react-query';
import { adminApi } from '../../api/admin';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/Table';
import { queryKeys, staleTime } from '../../lib/queryKeys';
import { sanitizeFilename } from '../../lib/sanitize';
import { PageHeader, QueryState } from './AdminUtils';
import { formatDate } from './adminFormat';

export default function HITLOverviewPage() {
  const queue = useQuery({
    queryKey: queryKeys.admin.hitlQueue,
    queryFn: async () => (await adminApi.getHITLQueue()).data,
    staleTime: staleTime.hitlQueue,
  });

  return (
    <div className="space-y-6">
      <PageHeader title="HITL Queue" description="Reports waiting for human verification." />
      <QueryState
        isLoading={queue.isLoading}
        isError={queue.isError}
        error={queue.error}
        onRetry={() => void queue.refetch()}
        isEmpty={(queue.data ?? []).length === 0}
        emptyTitle="No HITL reports pending"
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Report</TableHead>
              <TableHead>Patient</TableHead>
              <TableHead>Doctor</TableHead>
              <TableHead>Fields Pending</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Uploaded</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(queue.data ?? []).map((item) => (
              <TableRow key={item.report_id}>
                <TableCell className="font-medium">{sanitizeFilename(item.file_name)}</TableCell>
                <TableCell className="font-mono text-xs">{item.patient_id}</TableCell>
                <TableCell className="font-mono text-xs">{item.doctor_id ?? '-'}</TableCell>
                <TableCell>{item.hitl_count}</TableCell>
                <TableCell>{item.lifecycle_status}</TableCell>
                <TableCell>{formatDate(item.first_uploaded_at)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </QueryState>
    </div>
  );
}
