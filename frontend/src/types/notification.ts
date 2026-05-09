export interface NotificationItem {
  notification_id: string;
  type: string;
  title: string;
  message: string;
  report_id: string | null;
  is_read: boolean;
  created_at: string;
}
