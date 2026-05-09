/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { notificationsApi } from '../api/notifications';
import { normalizeApiError } from '../lib/apiError';
import { queryKeys } from '../lib/queryKeys';
import { useAuthStore } from '../store/authStore';
import type { NotificationItem } from '../types/notification';

interface RealtimeContextValue {
  isConnected: boolean;
}

const RealtimeContext = createContext<RealtimeContextValue>({ isConnected: true });
const NORMAL_POLL_MS = 60_000;
const MAX_RETRY_MS = 5 * 60_000;

function mergeNotifications(
  existing: NotificationItem[] = [],
  incoming: NotificationItem[],
): NotificationItem[] {
  const merged = new Map<string, NotificationItem>();

  for (const notification of existing) {
    merged.set(notification.notification_id, notification);
  }
  for (const notification of incoming) {
    merged.set(notification.notification_id, notification);
  }

  return Array.from(merged.values())
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 50);
}

export function RealtimeProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const timeoutRef = useRef<number | undefined>();
  const failureCountRef = useRef(0);
  const [isConnected, setIsConnected] = useState(true);

  const poll = useCallback(async () => {
    if (!user || user.role === 'admin' || document.visibilityState === 'hidden') {
      return;
    }

    try {
      const response = user.role === 'doctor'
        ? await notificationsApi.getDoctorNotifications()
        : await notificationsApi.getPatientNotifications();

      failureCountRef.current = 0;
      setIsConnected(true);
      queryClient.setQueryData<NotificationItem[]>(
        queryKeys.notifications.all(user.role),
        (current) => mergeNotifications(current, response.data),
      );
    } catch (error) {
      normalizeApiError(error);
      failureCountRef.current += 1;
      setIsConnected(false);
    }
  }, [queryClient, user]);

  useEffect(() => {
    window.clearTimeout(timeoutRef.current);
    failureCountRef.current = 0;

    if (!user || user.role === 'admin') {
      return undefined;
    }

    const scheduleNextPoll = () => {
      window.clearTimeout(timeoutRef.current);
      const retryDelay = Math.min(
        NORMAL_POLL_MS * 2 ** failureCountRef.current,
        MAX_RETRY_MS,
      );
      const delay = failureCountRef.current === 0 ? NORMAL_POLL_MS : retryDelay;

      timeoutRef.current = window.setTimeout(() => {
        void poll().finally(scheduleNextPoll);
      }, delay);
    };

    const resume = () => {
      if (document.visibilityState === 'visible') {
        void poll();
        scheduleNextPoll();
      }
    };

    void poll();
    scheduleNextPoll();
    document.addEventListener('visibilitychange', resume);
    window.addEventListener('focus', resume);

    return () => {
      window.clearTimeout(timeoutRef.current);
      document.removeEventListener('visibilitychange', resume);
      window.removeEventListener('focus', resume);
    };
  }, [poll, user]);

  return (
    <RealtimeContext.Provider value={{ isConnected }}>
      {children}
    </RealtimeContext.Provider>
  );
}

export const useRealtime = () => useContext(RealtimeContext);
