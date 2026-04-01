"use client";

import { useState, useEffect, useRef, useCallback } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
const WS_URL = API_URL.replace("http", "ws");

export type WSNotification = {
  id: string;
  user_id: string;
  title: string;
  body: string;
  action_url: string;
  read: boolean;
  created_at: string;
  metadata: Record<string, any>;
};

type UseNotificationsOpts = {
  userId?: string;
  /** Only surface notifications whose metadata matches these keys */
  filter?: Record<string, string>;
  /** Auto-reconnect delay in ms (default 3000) */
  reconnectDelay?: number;
};

/**
 * Real-time notification hook — connects to the backend WebSocket
 * and pushes new notifications into state.
 */
export function useNotifications(opts: UseNotificationsOpts = {}) {
  const { userId = "dev-user", filter, reconnectDelay = 3000 } = opts;
  const [notifications, setNotifications] = useState<WSNotification[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef<ReturnType<typeof setTimeout>>();

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(`${WS_URL}/ws/notifications`);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        ws.send(JSON.stringify({ user_id: userId }));
      };

      ws.onmessage = (ev) => {
        try {
          const notif: WSNotification = JSON.parse(ev.data);
          // Apply filter
          if (filter) {
            const meta = notif.metadata || {};
            const matches = Object.entries(filter).every(
              ([k, v]) => meta[k] === v
            );
            if (!matches) return;
          }
          setNotifications((prev) => [notif, ...prev].slice(0, 100));
        } catch {
          // ignore malformed messages
        }
      };

      ws.onclose = () => {
        setConnected(false);
        retryRef.current = setTimeout(connect, reconnectDelay);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      retryRef.current = setTimeout(connect, reconnectDelay);
    }
  }, [userId, filter, reconnectDelay]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(retryRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const clear = useCallback(() => setNotifications([]), []);

  return { notifications, connected, clear };
}

/**
 * Filtered hook for ingestion progress updates.
 * Returns only ingest-related notifications with progress metadata.
 */
export function useIngestProgress(jobId?: string) {
  const { notifications, connected } = useNotifications({
    filter: jobId ? { job_id: jobId } : undefined,
  });

  // Latest status per job
  const jobMap = new Map<string, WSNotification>();
  for (const n of notifications) {
    const jid = n.metadata?.job_id;
    if (jid && !jobMap.has(jid)) {
      jobMap.set(jid, n);
    }
  }

  return {
    jobs: Array.from(jobMap.values()),
    connected,
    latest: notifications[0] ?? null,
  };
}

/**
 * Filtered hook for workflow execution timeline updates.
 */
export function useWorkflowUpdates(workflowId?: string) {
  const { notifications, connected } = useNotifications({
    filter: workflowId ? { workflow_id: workflowId } : undefined,
  });

  return { events: notifications, connected };
}
