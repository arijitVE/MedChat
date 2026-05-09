import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { notificationsApi } from '../api/notifications';
import { normalizeApiError } from '../lib/apiError';
import { queryKeys, staleTime } from '../lib/queryKeys';
import type { ApiError } from '../lib/apiError';
import type { NotificationItem } from '../types/notification';

type NotificationRole = 'doctor' | 'patient';
type MarkReadVariables = {
  notificationId: string;
};
type NotificationContext = {
  previousNotifications?: NotificationItem[];
};

function markNotificationRead(role: NotificationRole, notificationId: string) {
  return role === 'doctor'
    ? notificationsApi.markDoctorRead(notificationId)
    : notificationsApi.markPatientRead(notificationId);
}

export function useNotifications(role: NotificationRole | undefined) {
  const queryClient = useQueryClient();
  const queryKey = queryKeys.notifications.all(role ?? 'guest');

  return useQuery<NotificationItem[]>({
    queryKey,
    queryFn: async () => queryClient.getQueryData<NotificationItem[]>(queryKey) ?? [],
    enabled: false,
    initialData: () => queryClient.getQueryData<NotificationItem[]>(queryKey) ?? [],
    staleTime: staleTime.notifications,
  });
}

export function useMarkNotificationRead(role: NotificationRole) {
  const queryClient = useQueryClient();
  const queryKey = queryKeys.notifications.all(role);

  return useMutation<NotificationItem, ApiError, MarkReadVariables, NotificationContext>({
    mutationFn: async ({ notificationId }) => {
      try {
        const response = await markNotificationRead(role, notificationId);
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    onMutate: async ({ notificationId }) => {
      await queryClient.cancelQueries({ queryKey });
      const previousNotifications = queryClient.getQueryData<NotificationItem[]>(queryKey);
      queryClient.setQueryData<NotificationItem[]>(
        queryKey,
        (notifications = []) =>
          notifications.map((notification) =>
            notification.notification_id === notificationId
              ? { ...notification, is_read: true }
              : notification,
          ),
      );
      return { previousNotifications };
    },
    onError: (_error, _variables, context) => {
      queryClient.setQueryData(queryKey, context?.previousNotifications);
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey });
    },
  });
}
