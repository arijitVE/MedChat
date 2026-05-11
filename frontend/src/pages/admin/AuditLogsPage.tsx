import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { adminApi } from '../../api/admin';
import { Pagination } from '../../components/ui/Pagination';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/Table';
import { queryKeys, staleTime } from '../../lib/queryKeys';
import { PageHeader, QueryState } from './AdminUtils';
import { formatDate } from './adminFormat';

const pageSize = 20;

export default function AuditLogsPage() {
  const [page, setPage] = useState(1);
  const filters = { page, page_size: pageSize };
  const logs = useQuery({
    queryKey: queryKeys.admin.auditLogs(filters),
    queryFn: async () => (await adminApi.getAuditLogs(filters)).data,
    staleTime: staleTime.usersList,
  });

  return (
    <div className="space-y-6">
      <PageHeader title="Audit Logs" description="Security and workflow audit events." />
      <QueryState
        isLoading={logs.isLoading}
        isError={logs.isError}
        error={logs.error}
        onRetry={() => void logs.refetch()}
        isEmpty={(logs.data?.items ?? []).length === 0}
        emptyTitle="No audit logs found"
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Action</TableHead>
              <TableHead>User</TableHead>
              <TableHead>Entity</TableHead>
              <TableHead>Report</TableHead>
              <TableHead>Created</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(logs.data?.items ?? []).map((log) => (
              <TableRow key={log.log_id}>
                <TableCell className="font-medium">{log.action}</TableCell>
                <TableCell>{log.user_role ?? '-'} {log.user_id ? `(${log.user_id})` : ''}</TableCell>
                <TableCell>{log.entity_type ?? '-'} {log.entity_id ? `(${log.entity_id})` : ''}</TableCell>
                <TableCell className="font-mono text-xs">{log.report_id ?? '-'}</TableCell>
                <TableCell>{formatDate(log.created_at)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </QueryState>
      <Pagination page={logs.data?.page ?? page} totalPages={logs.data?.total_pages ?? 1} onPageChange={setPage} />
    </div>
  );
}
