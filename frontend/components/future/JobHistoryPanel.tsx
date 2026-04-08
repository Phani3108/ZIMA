"use client";

import { useState } from "react";
import { RotateCcw, Pencil, Sparkles, X } from "lucide-react";

type Job = {
  id: string;
  brief: string;
  output_text: string;
  review_scores: Record<string, number>;
  created_at: string;
  status: string;
};

type Props = {
  suggestions: Job[];
  onUse: (jobId: string) => void;
  onEdit: (jobId: string) => void;
  onDismiss: () => void;
};

export default function JobHistoryPanel({ suggestions, onUse, onEdit, onDismiss }: Props) {
  if (!suggestions.length) return null;

  return (
    <div className="border border-amber-200 bg-amber-50/50 rounded-lg p-3 mb-3">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-amber-500" />
          <span className="text-sm font-medium text-amber-800">
            Recent outputs you can build on
          </span>
        </div>
        <button onClick={onDismiss} className="text-amber-400 hover:text-amber-600">
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="space-y-2">
        {suggestions.map((job) => (
          <div
            key={job.id}
            className="bg-white border border-amber-100 rounded-md p-3 text-sm"
          >
            <div className="text-gray-800 font-medium truncate mb-1">
              {job.brief}
            </div>
            <div className="text-gray-500 text-xs line-clamp-2 mb-2">
              {job.output_text}
            </div>

            {/* Score badges */}
            {job.review_scores && Object.keys(job.review_scores).length > 0 && (
              <div className="flex gap-1 mb-2 flex-wrap">
                {Object.entries(job.review_scores).map(([key, val]) => (
                  <span
                    key={key}
                    className="inline-block text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-600"
                  >
                    {key}: {val}/10
                  </span>
                ))}
              </div>
            )}

            <div className="flex gap-2">
              <button
                onClick={() => onUse(job.id)}
                className="flex items-center gap-1 text-xs px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                <RotateCcw className="w-3 h-3" />
                Use as-is
              </button>
              <button
                onClick={() => onEdit(job.id)}
                className="flex items-center gap-1 text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
              >
                <Pencil className="w-3 h-3" />
                Edit &amp; refine
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
