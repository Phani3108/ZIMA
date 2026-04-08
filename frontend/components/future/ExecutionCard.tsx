"use client";

import { useState } from "react";
import clsx from "clsx";
import { ChevronDown, ChevronRight, CheckCircle2, Loader2, Clock } from "lucide-react";

type AgentStep = {
  from: string;
  step_name: string;
  step_index: number;
  total_steps: number;
  status: "started" | "completed";
  preview?: string;
};

type Props = {
  agentName: string;
  avatar?: string;
  steps: AgentStep[];
  isActive?: boolean;
};

const STATUS_ICON = {
  started: <Loader2 className="w-4 h-4 animate-spin text-blue-500" />,
  completed: <CheckCircle2 className="w-4 h-4 text-green-500" />,
  pending: <Clock className="w-4 h-4 text-gray-300" />,
};

export default function ExecutionCard({ agentName, avatar, steps, isActive }: Props) {
  const [open, setOpen] = useState(true);

  const completed = steps.filter((s) => s.status === "completed").length;
  const total = steps.length > 0 ? steps[0].total_steps : 0;
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0;

  return (
    <div
      className={clsx(
        "border rounded-lg mb-2 transition-colors",
        isActive ? "border-blue-400 bg-blue-50/50" : "border-gray-200 bg-white"
      )}
    >
      {/* Header */}
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-3 py-2 text-left"
      >
        {open ? (
          <ChevronDown className="w-4 h-4 text-gray-400" />
        ) : (
          <ChevronRight className="w-4 h-4 text-gray-400" />
        )}
        <span className="text-base">{avatar || "🤖"}</span>
        <span className="font-medium text-sm text-gray-800 flex-1">{agentName}</span>
        <span className="text-xs text-gray-500">
          {completed}/{total}
        </span>
        {/* Mini progress bar */}
        <div className="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-500 rounded-full transition-all"
            style={{ width: `${pct}%` }}
          />
        </div>
      </button>

      {/* Steps */}
      {open && steps.length > 0 && (
        <div className="px-3 pb-2 space-y-1 ml-7">
          {steps.map((step, i) => (
            <div key={i} className="flex items-center gap-2 text-sm">
              {STATUS_ICON[step.status] || STATUS_ICON.pending}
              <span
                className={clsx(
                  step.status === "completed" ? "text-gray-600" : "text-gray-800 font-medium"
                )}
              >
                {step.step_name}
              </span>
              {step.preview && (
                <span className="text-xs text-gray-400 truncate max-w-[200px]">
                  — {step.preview}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
