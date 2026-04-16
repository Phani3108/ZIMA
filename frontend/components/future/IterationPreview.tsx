"use client";

import { ThumbsUp, RefreshCw, Pencil } from "lucide-react";
import { useState } from "react";

type Props = {
  iteration: number;
  output: string;
  imageUrl?: string;
  agentCommentary?: string;
  onProceed: () => void;
  onRetry: () => void;
  onAdjust: (feedback: string) => void;
};

export default function IterationPreview({
  iteration, output, imageUrl, agentCommentary, onProceed, onRetry, onAdjust,
}: Props) {
  const [adjustMode, setAdjustMode] = useState(false);
  const [feedback, setFeedback] = useState("");

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden animate-slide-in">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100 bg-gray-50">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-blue-600 bg-blue-50 px-2.5 py-1 rounded-full">
            Iteration {iteration}
          </span>
        </div>
        {agentCommentary && (
          <p className="text-[11px] text-gray-500 italic max-w-sm truncate">{agentCommentary}</p>
        )}
      </div>

      {/* Content preview */}
      <div className="p-5">
        {imageUrl && (
          <div className="mb-4 bg-gray-50 rounded-lg border border-gray-100 p-2 flex items-center justify-center">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={imageUrl}
              alt={`Iteration ${iteration}`}
              className="max-h-64 rounded-lg object-contain"
            />
          </div>
        )}

        {output && (
          <div className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap bg-gray-50 border border-gray-100 rounded-lg p-4">
            {output}
          </div>
        )}
      </div>

      {/* Adjust input */}
      {adjustMode && (
        <div className="px-5 pb-2 animate-slide-in">
          <textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            rows={2}
            placeholder="Tell the agent what to adjust..."
            className="w-full text-sm border border-gray-200 rounded-lg p-3 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400 resize-none"
          />
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 px-5 py-3 border-t border-gray-100">
        <button
          onClick={() => {
            if (adjustMode && feedback.trim()) {
              onAdjust(feedback);
              setAdjustMode(false);
              setFeedback("");
            } else {
              onProceed();
            }
          }}
          className="flex items-center gap-1.5 text-xs font-medium px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
        >
          <ThumbsUp className="w-3 h-3" />
          {adjustMode ? "Send Feedback" : "Looks Good"}
        </button>
        <button
          onClick={onRetry}
          className="flex items-center gap-1.5 text-xs font-medium px-3 py-2 border border-gray-200 text-gray-600 rounded-lg hover:bg-gray-50 transition-colors"
        >
          <RefreshCw className="w-3 h-3" />
          Try Another Angle
        </button>
        <button
          onClick={() => setAdjustMode(!adjustMode)}
          className="flex items-center gap-1.5 text-xs font-medium px-3 py-2 border border-gray-200 text-gray-600 rounded-lg hover:bg-gray-50 transition-colors"
        >
          <Pencil className="w-3 h-3" />
          {adjustMode ? "Cancel" : "Adjust"}
        </button>
      </div>
    </div>
  );
}
