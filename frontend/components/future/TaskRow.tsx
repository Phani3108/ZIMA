"use client";

import { useState } from "react";
import clsx from "clsx";
import { ChevronDown, ChevronRight, ExternalLink } from "lucide-react";

export type RecentTask = {
  id: string;
  title: string;
  status: "complete" | "in_progress" | "awaiting_review" | "failed";
  time_ago: string;
  iterations: number;
  score: number | null;
  prompt: string;
  tools: string[];
  output_url?: string;
};

const STATUS = {
  complete:         { emoji: "🟢", label: "Complete",         cls: "text-green-600 bg-green-50 border-green-200" },
  in_progress:      { emoji: "🔵", label: "In Progress",      cls: "text-blue-600 bg-blue-50 border-blue-200" },
  awaiting_review:  { emoji: "🟡", label: "Awaiting Review",  cls: "text-amber-600 bg-amber-50 border-amber-200" },
  failed:           { emoji: "🔴", label: "Failed",           cls: "text-red-600 bg-red-50 border-red-200" },
};

export default function TaskRow({ task }: { task: RecentTask }) {
  const [promptOpen, setPromptOpen] = useState(false);
  const s = STATUS[task.status];

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 transition-shadow hover:shadow-sm">
      {/* Top row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-medium text-gray-800 truncate">{task.title}</h4>
          <div className="flex items-center gap-2 mt-1 text-[11px] text-gray-500">
            <span>{task.time_ago}</span>
            <span className="text-gray-300">•</span>
            <span>{task.iterations} iteration{task.iterations !== 1 ? "s" : ""}</span>
            {task.score !== null && (
              <>
                <span className="text-gray-300">•</span>
                <span>Score: {task.score.toFixed(1)}</span>
              </>
            )}
          </div>
        </div>
        <span className={clsx("text-[10px] font-medium px-2 py-0.5 rounded-full border", s.cls)}>
          {s.emoji} {s.label}
        </span>
      </div>

      {/* Action row */}
      <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-100">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setPromptOpen(!promptOpen)}
            className="flex items-center gap-1 text-[11px] font-medium text-gray-600 hover:text-blue-600 transition-colors"
          >
            {promptOpen ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
            Prompt
          </button>
          <div className="flex gap-1 ml-2">
            {task.tools.map((t) => (
              <span
                key={t}
                className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-600"
              >
                {t}
              </span>
            ))}
          </div>
        </div>

        {task.output_url && (
          <a
            href={task.output_url}
            className="flex items-center gap-1 text-[11px] font-medium text-blue-600 hover:text-blue-700"
          >
            View Output <ExternalLink className="w-3 h-3" />
          </a>
        )}
      </div>

      {/* Expandable prompt */}
      {promptOpen && (
        <div className="mt-3 bg-gray-50 border border-gray-100 rounded-lg p-3 text-xs text-gray-700 leading-relaxed whitespace-pre-wrap animate-slide-in">
          {task.prompt}
        </div>
      )}
    </div>
  );
}
