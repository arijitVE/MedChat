import { useMarkNotificationRead, useNotifications } from '../../hooks/useNotifications';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { EmptyState } from '../../components/ui/EmptyState';
import { Skeleton } from '../../components/ui/Skeleton';
import { RetryPanel } from '../../components/feedback/RetryPanel';
import { normalizeApiError } from '../../lib/apiError';

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

export default function DoctorNotificationsPage() {
  const notifications = useNotifications('doctor');
  const markRead = useMarkNotificationRead('doctor');

  if (notifications.isError) {
    return <RetryPanel onRetry={() => void notifications.refetch()} message={normalizeApiError(notifications.error).message} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-clinical-text-primary">Notifications</h1>
        <p className="mt-1 text-sm text-clinical-text-secondary">HITL requests, failed processing alerts, assignments, and system updates.</p>
      </div>
      {notifications.isLoading ? (
        <Skeleton variant="card" rows={5} />
      ) : (notifications.data ?? []).length === 0 ? (
        <EmptyState title="No notifications yet" />
      ) : (
        <div className="grid gap-3">
          {(notifications.data ?? []).map((notification) => (
            <Card key={notification.notification_id} className={notification.is_read ? '' : 'border-clinical-primary'}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-clinical-text-primary">{notification.title}</p>
                  <p className="mt-1 text-sm text-clinical-text-secondary">{notification.message}</p>
                  <p className="mt-2 text-xs text-clinical-text-muted">{formatDate(notification.created_at)}</p>
                </div>
                {!notification.is_read ? (
                  <Button
                    variant="secondary"
                    className="min-h-8 px-3 py-1"
                    loading={markRead.isPending}
                    onClick={() => markRead.mutate({ notificationId: notification.notification_id })}
                  >
                    Mark as read
                  </Button>
                ) : null}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
