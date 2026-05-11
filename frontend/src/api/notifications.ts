import { apiClient } from './client';
import type { NotificationItem, NotificationList } from '../types/notification';

export { type NotificationItem };

export const notificationsApi = {
  getDoctorNotifications: () =>
    apiClient.get<NotificationList>('/doctor/notifications').then((response) => ({
      ...response,
      data: response.data.notifications,
    })),
  fetchDoctorNotifications: () =>
    apiClient.get<NotificationList>('/doctor/notifications').then((response) => ({
      ...response,
      data: response.data.notifications,
    })),
  markDoctorRead: (notificationId: string) =>
    apiClient.put<NotificationItem>(`/doctor/notifications/${notificationId}/read`),
  markDoctorNotificationRead: (notificationId: string) =>
    apiClient.put<NotificationItem>(`/doctor/notifications/${notificationId}/read`),
  getPatientNotifications: () =>
    apiClient.get<NotificationList>('/patient/notifications').then((response) => ({
      ...response,
      data: response.data.notifications,
    })),
  fetchMyNotifications: () =>
    apiClient.get<NotificationList>('/patient/notifications').then((response) => ({
      ...response,
      data: response.data.notifications,
    })),
  markPatientRead: (notificationId: string) =>
    apiClient.put<NotificationItem>(`/patient/notifications/${notificationId}/read`),
  markNotificationRead: (notificationId: string) =>
    apiClient.put<NotificationItem>(`/patient/notifications/${notificationId}/read`),
};
