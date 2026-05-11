import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { adminApi } from '../../api/admin';
import { Pagination } from '../../components/ui/Pagination';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/Table';
import { queryKeys, staleTime } from '../../lib/queryKeys';
import { PageHeader, QueryState } from './AdminUtils';
import { formatDate } from './adminFormat';

const pageSize = 20;

export default function NotificationsPage() {
  const [page, setPage] = useState(1);
  const filters = { page, page_size: pageSize };
  const notifications = useQuery({
    queryKey: queryKeys.admin.notifications(filters),
    queryFn: async () => (await adminApi.getNotifications(filters)).data,
    staleTime: staleTime.notifications,
  });

  return (
    <div className="space-y-6">
      <PageHeader title="Notifications" description="System notifications sent to users." />
      <QueryState
        isLoading={notifications.isLoading}
        isError={notifications.isError}
        error={notifications.error}
        onRetry={() => void notifications.refetch()}
        isEmpty={(notifications.data?.items ?? []).length === 0}
        emptyTitle="No notifications found"
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Title</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Recipient</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Created</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(notifications.data?.items ?? []).map((item) => (
              <TableRow key={item.notification_id}>
                <TableCell className="font-medium">{item.title}</TableCell>
                <TableCell>{item.type}</TableCell>
                <TableCell className="font-mono text-xs">{item.recipient_id}</TableCell>
                <TableCell>{item.is_read ? 'Read' : 'Unread'}</TableCell>
                <TableCell>{formatDate(item.created_at)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </QueryState>
      <Pagination page={notifications.data?.page ?? page} totalPages={notifications.data?.total_pages ?? 1} onPageChange={setPage} />
    </div>
  );
}
