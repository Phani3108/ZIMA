"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { Bell, Check, X } from "lucide-react";
import clsx from "clsx";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
const WS_URL = API_URL.replace("http", "ws");

type Notification = {
  id: string;
  title: string;
  body: string;
  action_url: string;
  read: boolean;
  created_at: string;
  metadata: Record<string, any>;
};

export default function NotificationBell() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Fetch initial notifications
  useEffect(() => {
    fetch("/api/notifications?limit=20")
      .then((r) => r.json())
      .then((data) => {
        setNotifications(data);
        setUnreadCount(data.filter((n: Notification) => !n.read).length);
      })
      .catch(() => {});
  }, []);

  // WebSocket for real-time updates
  useEffect(() => {
    try {
      const ws = new WebSocket(`${WS_URL}/ws/notifications`);
      wsRef.current = ws;

      ws.onopen = () => {
        ws.send(JSON.stringify({ user_id: "dev-user" }));
      };

      ws.onmessage = (ev) => {
        const notif = JSON.parse(ev.data);
        setNotifications((prev) => [notif, ...prev].slice(0, 50));
        setUnreadCount((c) => c + 1);
      };

      return () => ws.close();
    } catch {
      // WebSocket not available
    }
  }, []);

  // Close on click outside
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const markRead = async (id: string) => {
    await fetch(`/api/notifications/${id}/read`, { method: "POST" });
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
    setUnreadCount((c) => Math.max(0, c - 1));
  };

  const markAllRead = async () => {
    await fetch("/api/notifications/read-all", { method: "POST" });
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    setUnreadCount(0);
  };

  return (
    <div className="relative" ref={panelRef}>
      <button
        onClick={() => setOpen(!open)}
        className="relative p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
      >
        <Bell size={16} className="text-gray-500" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-red-500 text-white text-[9px] font-bold rounded-full flex items-center justify-center">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-9 w-80 bg-white border rounded-xl shadow-lg z-50 max-h-96 overflow-hidden flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-2.5 border-b bg-gray-50">
            <span className="text-sm font-semibold text-gray-700">Notifications</span>
            {unreadCount > 0 && (
              <button
                onClick={markAllRead}
                className="text-[11px] text-brand hover:underline flex items-center gap-1"
              >
                <Check size={10} /> Mark all read
              </button>
            )}
          </div>

          {/* List */}
          <div className="overflow-y-auto flex-1">
            {notifications.length === 0 ? (
              <div className="text-center py-8 text-gray-400 text-xs">
                No notifications
              </div>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.id}
                  className={clsx(
                    "px-4 py-3 border-b last:border-0 transition-colors",
                    n.read ? "bg-white" : "bg-blue-50/50"
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      {n.action_url ? (
                        <Link
                          href={n.action_url}
                          onClick={() => { markRead(n.id); setOpen(false); }}
                          className="text-sm font-medium text-gray-900 hover:text-brand line-clamp-1"
                        >
                          {n.title}
                        </Link>
                      ) : (
                        <p className="text-sm font-medium text-gray-900 line-clamp-1">{n.title}</p>
                      )}
                      <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{n.body}</p>
                      <p className="text-[10px] text-gray-400 mt-1">
                        {new Date(n.created_at).toLocaleTimeString()}
                      </p>
                    </div>
                    {!n.read && (
                      <button
                        onClick={() => markRead(n.id)}
                        className="text-gray-400 hover:text-gray-600 shrink-0 mt-0.5"
                      >
                        <X size={12} />
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
