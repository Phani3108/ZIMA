"use client";

import clsx from "clsx";

type MeetingMessage = {
  agent_id: string;
  agent_title: string;
  avatar: string;
  content: string;
  timestamp: string;
};

type MeetingPlan = {
  tasks?: Array<{ step: number; agent: string; action: string }>;
  estimated_duration?: string;
  summary?: string;
};

export default function MeetingTranscript({
  transcript,
  plan,
}: {
  transcript: MeetingMessage[];
  plan?: MeetingPlan;
}) {
  return (
    <div className="space-y-4">
      {/* Transcript */}
      <div className="space-y-3">
        {transcript.map((msg, i) => (
          <div key={i} className="flex gap-3 items-start">
            <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-lg shrink-0">
              {msg.avatar || "🤖"}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-gray-900">
                  {msg.agent_title}
                </span>
                <span className="text-[10px] text-gray-400">
                  {msg.timestamp
                    ? new Date(msg.timestamp).toLocaleTimeString()
                    : ""}
                </span>
              </div>
              <p className="text-sm text-gray-700 mt-0.5">{msg.content}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Plan summary */}
      {plan && (plan.tasks?.length || plan.summary) && (
        <div className="border-t pt-4 mt-4">
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
            Execution Plan
          </h4>
          {plan.summary && (
            <p className="text-sm text-gray-700 mb-3">{plan.summary}</p>
          )}
          {plan.tasks && plan.tasks.length > 0 && (
            <div className="space-y-1.5">
              {plan.tasks.map((task, i) => (
                <div
                  key={i}
                  className="flex items-center gap-2 text-sm text-gray-600"
                >
                  <span className="w-5 h-5 rounded-full bg-blue-50 text-blue-700 text-[10px] font-bold flex items-center justify-center shrink-0">
                    {task.step}
                  </span>
                  <span className="font-medium text-gray-800">
                    {task.agent}
                  </span>
                  <span className="text-gray-400">→</span>
                  <span className="truncate">{task.action}</span>
                </div>
              ))}
            </div>
          )}
          {plan.estimated_duration && (
            <p className="text-xs text-gray-400 mt-2">
              Est. duration: {plan.estimated_duration}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
