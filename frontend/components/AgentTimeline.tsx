"use client";

import clsx from "clsx";

type TimelineEvent = {
  agent: string;
  title: string;
  avatar: string;
  type: string;
  summary: string;
  timestamp: string;
};

const TYPE_COLORS: Record<string, string> = {
  handoff: "border-blue-400",
  response: "border-green-400",
  feedback: "border-amber-400",
  discussion: "border-purple-400",
  delegation: "border-indigo-400",
  question: "border-pink-400",
  status_update: "border-gray-400",
};

const TYPE_LABELS: Record<string, string> = {
  handoff: "Handoff",
  response: "Response",
  feedback: "Feedback",
  discussion: "Discussion",
  delegation: "Delegation",
  question: "Question",
  status_update: "Status",
};

export default function AgentTimeline({ events }: { events: TimelineEvent[] }) {
  if (!events.length) {
    return (
      <div className="text-sm text-gray-400 py-4 text-center">
        No agent activity yet.
      </div>
    );
  }

  return (
    <div className="relative pl-6">
      {/* Vertical line */}
      <div className="absolute left-3 top-0 bottom-0 w-px bg-gray-200" />

      <div className="space-y-4">
        {events.map((ev, i) => (
          <div key={i} className="relative flex gap-3 items-start">
            {/* Dot on timeline */}
            <div
              className={clsx(
                "absolute -left-3 top-1 w-6 h-6 rounded-full flex items-center justify-center text-xs border-2 bg-white",
                TYPE_COLORS[ev.type] || "border-gray-300"
              )}
              title={ev.title || ev.agent}
            >
              {ev.avatar || "🤖"}
            </div>

            <div className="ml-5 flex-1 min-w-0">
              <div className="flex items-center gap-2 text-xs">
                <span className="font-medium text-gray-900">
                  {ev.title || ev.agent}
                </span>
                <span
                  className={clsx(
                    "px-1.5 py-0.5 rounded text-[10px] font-medium",
                    ev.type === "feedback"
                      ? "bg-amber-50 text-amber-700"
                      : ev.type === "handoff"
                      ? "bg-blue-50 text-blue-700"
                      : "bg-gray-50 text-gray-600"
                  )}
                >
                  {TYPE_LABELS[ev.type] || ev.type}
                </span>
                {ev.timestamp && (
                  <span className="text-gray-400 text-[10px]">
                    {new Date(ev.timestamp).toLocaleTimeString()}
                  </span>
                )}
              </div>
              {ev.summary && (
                <p className="text-sm text-gray-600 mt-0.5 line-clamp-2">
                  {ev.summary}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
