"use client";

import clsx from "clsx";
import { Lightbulb, Wrench, Eye, CheckCircle2, Loader2 } from "lucide-react";

export type NarrationEntry = {
  id: string;
  type: "thinking" | "tool" | "observation" | "milestone";
  text: string;
  detail?: string;
  timestamp?: string;
};

const TYPE_META = {
  thinking:    { icon: Lightbulb,    color: "text-purple-500", bg: "bg-purple-50 border-purple-100" },
  tool:        { icon: Wrench,       color: "text-blue-500",   bg: "bg-blue-50 border-blue-100" },
  observation: { icon: Eye,          color: "text-amber-500",  bg: "bg-amber-50 border-amber-100" },
  milestone:   { icon: CheckCircle2, color: "text-green-500",  bg: "bg-green-50 border-green-100" },
};

type Props = {
  entries: NarrationEntry[];
  streaming?: boolean; // show typing indicator at bottom
};

export default function AgentNarration({ entries, streaming }: Props) {
  return (
    <div className="space-y-2">
      {entries.map((entry) => {
        const meta = TYPE_META[entry.type];
        const Icon = meta.icon;

        return (
          <div
            key={entry.id}
            className={clsx("flex gap-2.5 rounded-xl border p-3 animate-slide-in", meta.bg)}
          >
            <Icon className={clsx("w-4 h-4 mt-0.5 shrink-0", meta.color)} />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-800 leading-relaxed">{entry.text}</p>
              {entry.detail && (
                <p className="text-xs text-gray-500 mt-1">{entry.detail}</p>
              )}
            </div>
            {entry.timestamp && (
              <span className="text-[10px] text-gray-400 shrink-0 mt-0.5">{entry.timestamp}</span>
            )}
          </div>
        );
      })}

      {/* Typing indicator */}
      {streaming && (
        <div className="flex items-center gap-2 text-gray-400 pl-3 py-2">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          <span className="text-xs">Agent is thinking...</span>
        </div>
      )}
    </div>
  );
}
