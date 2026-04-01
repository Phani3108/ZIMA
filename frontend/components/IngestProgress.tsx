"use client";

import { useIngestProgress, type WSNotification } from "@/lib/useNotifications";
import { CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import clsx from "clsx";

function ProgressBar({ pct }: { pct: number }) {
  return (
    <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
      <div
        className="h-full bg-blue-500 rounded-full transition-all duration-500 ease-out"
        style={{ width: `${Math.min(100, Math.max(0, pct))}%` }}
      />
    </div>
  );
}

function JobRow({ notif }: { notif: WSNotification }) {
  const meta = notif.metadata || {};
  const status = meta.status || "pending";
  const pct = meta.progress_pct || 0;
  const step = meta.current_step || "";
  const eta = meta.estimated_seconds_remaining;
  const source = meta.source_name || notif.title || "Unknown";

  return (
    <div className="bg-white border border-gray-200 rounded-lg px-4 py-3">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-sm font-medium text-gray-800 truncate max-w-xs">
          {source}
        </span>
        <span
          className={clsx(
            "flex items-center gap-1 text-xs font-medium",
            status === "done"
              ? "text-green-600"
              : status === "error"
              ? "text-red-600"
              : "text-blue-600"
          )}
        >
          {status === "done" ? (
            <CheckCircle size={12} />
          ) : status === "error" ? (
            <AlertCircle size={12} />
          ) : (
            <Loader2 size={12} className="animate-spin" />
          )}
          {status === "done"
            ? "Complete"
            : status === "error"
            ? "Failed"
            : `${pct}%`}
        </span>
      </div>

      {status !== "done" && status !== "error" && (
        <>
          <ProgressBar pct={pct} />
          <div className="flex items-center justify-between mt-1 text-[11px] text-gray-400">
            <span>{step}</span>
            {eta != null && eta > 0 && (
              <span>~{eta < 60 ? `${eta}s` : `${Math.ceil(eta / 60)}m`} remaining</span>
            )}
          </div>
        </>
      )}

      {status === "done" && meta.total_chunks && (
        <p className="text-xs text-gray-500 mt-1">
          {meta.total_chunks} chunks indexed
        </p>
      )}
    </div>
  );
}

export default function IngestProgress() {
  const { jobs, connected } = useIngestProgress();

  if (!jobs.length) return null;

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 mb-1">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
          Live Ingestion
        </h3>
        <span
          className={clsx(
            "w-1.5 h-1.5 rounded-full",
            connected ? "bg-green-400" : "bg-gray-300"
          )}
          title={connected ? "Connected" : "Disconnected"}
        />
      </div>
      {jobs.map((n) => (
        <JobRow key={n.metadata?.job_id || n.id} notif={n} />
      ))}
    </div>
  );
}
