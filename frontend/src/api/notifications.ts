import { apiClient } from './client';
import type { NotificationItem } from '../types/notification';

export { type NotificationItem };

export const notificationsApi = {
  getDoctorNotifications: () =>
    apiClient.get<NotificationItem[]>('/doctor/notifications'),
  fetchDoctorNotifications: () =>
    apiClient.get<NotificationItem[]>('/doctor/notifications'),
  markDoctorRead: (notificationId: string) =>
    apiClient.put<NotificationItem>(`/doctor/notifications/${notificationId}/read`),
  markDoctorNotificationRead: (notificationId: string) =>
    apiClient.put<NotificationItem>(`/doctor/notifications/${notificationId}/read`),
  getPatientNotifications: () =>
    apiClient.get<NotificationItem[]>('/patient/notifications'),
  fetchMyNotifications: () =>
    apiClient.get<NotificationItem[]>('/patient/notifications'),
  markPatientRead: (notificationId: string) =>
    apiClient.put<NotificationItem>(`/patient/notifications/${notificationId}/read`),
  markNotificationRead: (notificationId: string) =>
    apiClient.put<NotificationItem>(`/patient/notifications/${notificationId}/read`),
};
