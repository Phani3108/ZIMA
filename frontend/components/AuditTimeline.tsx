"use client";

import { useState, useEffect } from "react";
import {
  Clock, CheckCircle2, XCircle, Play, AlertTriangle,
  User, Bot, Settings, ChevronDown,
} from "lucide-react";
import clsx from "clsx";

type AuditEntry = {
  id: string;
  timestamp: string;
  actor: string;
  action: string;
  resource_type: string;
  resource_id: string;
  details: Record<string, any>;
};

const ACTION_CONFIG: Record<string, { icon: any; color: string; label: string }> = {
  created: { icon: Play, color: "text-blue-500", label: "Created" },
  stage_completed: { icon: CheckCircle2, color: "text-green-500", label: "Completed" },
  approved: { icon: CheckCircle2, color: "text-green-600", label: "Approved" },
  rejected: { icon: XCircle, color: "text-red-500", label: "Rejected" },
  published: { icon: CheckCircle2, color: "text-brand", label: "Published" },
  escalated: { icon: AlertTriangle, color: "text-amber-500", label: "Escalated" },
  configured: { icon: Settings, color: "text-gray-500", label: "Configured" },
  edited: { icon: Bot, color: "text-purple-500", label: "Edited" },
};

export default function AuditTimeline({ workflowId }: { workflowId: string }) {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    fetch(`/api/audit/workflow/${workflowId}`)
      .then((r) => r.json())
      .then((data) => {
        setEntries(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [workflowId]);

  if (loading) return null;
  if (entries.length === 0) return null;

  const visible = expanded ? entries : entries.slice(0, 5);

  return (
    <div className="bg-white border rounded-xl p-4 mt-6">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Audit Trail</h3>
      <div className="space-y-0">
        {visible.map((entry, i) => {
          const config = ACTION_CONFIG[entry.action] || {
            icon: Clock,
            color: "text-gray-400",
            label: entry.action,
          };
          const Icon = config.icon;
          const isAgent = !entry.actor.includes("-") && !entry.actor.includes("@");

          return (
            <div key={entry.id} className="flex gap-3 pb-3 last:pb-0">
              {/* Timeline line + dot */}
              <div className="flex flex-col items-center">
                <div className={clsx("w-6 h-6 rounded-full flex items-center justify-center bg-gray-50 border", config.color)}>
                  <Icon size={12} />
                </div>
                {i < visible.length - 1 && (
                  <div className="w-px h-full bg-gray-200 my-0.5" />
                )}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0 pb-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-gray-700">
                    {config.label}
                  </span>
                  <span className="text-[10px] text-gray-400 flex items-center gap-0.5">
                    {isAgent ? <Bot size={9} /> : <User size={9} />}
                    {entry.actor}
                  </span>
                  <span className="text-[10px] text-gray-300 ml-auto">
                    {new Date(entry.timestamp).toLocaleString()}
                  </span>
                </div>
                {entry.details && Object.keys(entry.details).length > 0 && (
                  <div className="text-[11px] text-gray-500 mt-0.5">
                    {entry.details.comment && <span>"{entry.details.comment}"</span>}
                    {entry.details.llm_used && <span className="ml-1">via {entry.details.llm_used}</span>}
                    {entry.details.status && <span className="ml-1">→ {entry.details.status}</span>}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {entries.length > 5 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 text-xs text-brand hover:underline mt-2"
        >
          <ChevronDown size={12} className={expanded ? "rotate-180" : ""} />
          {expanded ? "Show less" : `Show all ${entries.length} events`}
        </button>
      )}
    </div>
  );
}
