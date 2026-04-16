"use client";

import { useState } from "react";
import clsx from "clsx";
import { CheckCircle2, Circle, Clock, Pencil, ThumbsUp, XCircle } from "lucide-react";

export type PlanStep = {
  id: string;
  label: string;
  tool?: string;
  estimated?: string; // "~30s"
  status: "pending" | "active" | "done";
};

type Props = {
  agentName: string;
  avatar: string;
  summary: string;
  estimatedTime?: string;
  steps: PlanStep[];
  onApprove: () => void;
  onModify: (feedback: string) => void;
  onCancel: () => void;
};

const STEP_ICON = {
  pending: <Circle className="w-4 h-4 text-gray-300" />,
  active:  <Clock className="w-4 h-4 text-blue-500 animate-pulse" />,
  done:    <CheckCircle2 className="w-4 h-4 text-green-500" />,
};

export default function AgentPlanCard({ agentName, avatar, summary, estimatedTime, steps, onApprove, onModify, onCancel }: Props) {
  const [modifying, setModifying] = useState(false);
  const [feedback, setFeedback] = useState("");

  return (
    <div className="bg-white border border-blue-200 rounded-xl p-5 shadow-sm animate-slide-in">
      {/* Header */}
      <div className="flex items-center gap-2.5 mb-3">
        <span className="text-2xl">{avatar}</span>
        <div>
          <p className="text-sm font-semibold text-gray-800">{agentName}&apos;s Plan</p>
          {estimatedTime && (
            <p className="text-[11px] text-gray-500 flex items-center gap-1 mt-0.5">
              <Clock className="w-3 h-3" /> Est. {estimatedTime}
            </p>
          )}
        </div>
      </div>

      {/* Summary */}
      <p className="text-sm text-gray-700 leading-relaxed mb-4">{summary}</p>

      {/* Steps */}
      <div className="space-y-2 mb-5">
        {steps.map((step, i) => (
          <div key={step.id} className="flex items-start gap-2.5">
            <div className="mt-0.5">{STEP_ICON[step.status]}</div>
            <div className="flex-1 min-w-0">
              <p className={clsx("text-sm", step.status === "done" ? "text-gray-500 line-through" : "text-gray-800")}>
                {i + 1}. {step.label}
              </p>
              <div className="flex items-center gap-2 mt-0.5">
                {step.tool && (
                  <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">
                    {step.tool}
                  </span>
                )}
                {step.estimated && (
                  <span className="text-[10px] text-gray-400">{step.estimated}</span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Modify input */}
      {modifying && (
        <div className="mb-4 animate-slide-in">
          <textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            rows={2}
            placeholder="Tell the agent what to change..."
            className="w-full text-sm border border-gray-200 rounded-lg p-3 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400 resize-none"
          />
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => {
            if (modifying && feedback.trim()) {
              onModify(feedback);
              setModifying(false);
              setFeedback("");
            } else {
              onApprove();
            }
          }}
          className="flex items-center gap-1.5 text-xs font-medium px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <ThumbsUp className="w-3 h-3" />
          {modifying ? "Submit Changes" : "Looks Good, Go"}
        </button>
        <button
          onClick={() => setModifying(!modifying)}
          className="flex items-center gap-1.5 text-xs font-medium px-3 py-2 border border-gray-200 text-gray-600 rounded-lg hover:bg-gray-50 transition-colors"
        >
          <Pencil className="w-3 h-3" />
          {modifying ? "Cancel Edit" : "Modify"}
        </button>
        <button
          onClick={onCancel}
          className="flex items-center gap-1.5 text-xs font-medium px-3 py-2 text-gray-400 hover:text-red-500 transition-colors ml-auto"
        >
          <XCircle className="w-3 h-3" />
          Cancel
        </button>
      </div>
    </div>
  );
}
