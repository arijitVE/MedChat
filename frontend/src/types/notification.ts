export interface NotificationItem {
  notification_id: string;
  recipient_id?: string;
  sender_id?: string | null;
  type: string;
  title: string;
  message: string;
  report_id: string | null;
  is_read: boolean;
  created_at: string;
}

export interface NotificationList {
  notifications: NotificationItem[];
  unread_count: number;
}
