import { useEffect } from 'react';

type RealtimeEventType = 'report_processed' | 'field_updated' | 'assignment_changed';

export function useRealtimeEvent(
  event: RealtimeEventType,
  handler: (payload: unknown) => void,
) {
  useEffect(() => {
    void event;
    void handler;
    // WebSocket subscription is intentionally deferred to the realtime phase.
  }, [event, handler]);
}
