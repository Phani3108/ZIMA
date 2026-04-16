"use client";

import { useState } from "react";
import { Send, HelpCircle } from "lucide-react";

export type AgentQuestion = {
  id: string;
  label: string;
  hint?: string;
  type: "text" | "select" | "multiselect";
  options?: string[];
  required?: boolean;
};

type Props = {
  agentName: string;
  avatar: string;
  preamble?: string;
  questions: AgentQuestion[];
  onSubmit: (answers: Record<string, string | string[]>) => void;
};

export default function AgentQuestionForm({ agentName, avatar, preamble, questions, onSubmit }: Props) {
  const [answers, setAnswers] = useState<Record<string, string | string[]>>({});

  const set = (id: string, val: string | string[]) =>
    setAnswers((a) => ({ ...a, [id]: val }));

  const canSubmit = questions.filter((q) => q.required).every((q) => {
    const v = answers[q.id];
    return v && (typeof v === "string" ? v.trim() : v.length > 0);
  });

  return (
    <div className="bg-white border border-amber-200 rounded-xl p-5 animate-slide-in">
      {/* Header */}
      <div className="flex items-center gap-2.5 mb-3">
        <span className="text-2xl">{avatar}</span>
        <div>
          <p className="text-sm font-semibold text-gray-800">{agentName} has a few questions</p>
          {preamble && <p className="text-xs text-gray-500 mt-0.5">{preamble}</p>}
        </div>
      </div>

      {/* Questions */}
      <div className="space-y-4 mt-4">
        {questions.map((q) => (
          <div key={q.id}>
            <label className="flex items-center gap-1.5 text-sm font-medium text-gray-700 mb-1.5">
              {q.label}
              {q.required && <span className="text-red-400">*</span>}
              {q.hint && (
                <span title={q.hint}>
                  <HelpCircle className="w-3.5 h-3.5 text-gray-300" />
                </span>
              )}
            </label>

            {q.type === "text" && (
              <input
                type="text"
                value={(answers[q.id] as string) || ""}
                onChange={(e) => set(q.id, e.target.value)}
                className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400"
                placeholder={q.hint || ""}
              />
            )}

            {q.type === "select" && q.options && (
              <div className="flex flex-wrap gap-2">
                {q.options.map((opt) => {
                  const selected = answers[q.id] === opt;
                  return (
                    <button
                      key={opt}
                      onClick={() => set(q.id, opt)}
                      className={
                        selected
                          ? "text-xs px-3 py-1.5 rounded-lg border border-blue-300 bg-blue-50 text-blue-700 font-medium"
                          : "text-xs px-3 py-1.5 rounded-lg border border-gray-200 bg-white text-gray-600 hover:bg-gray-50"
                      }
                    >
                      {opt}
                    </button>
                  );
                })}
              </div>
            )}

            {q.type === "multiselect" && q.options && (
              <div className="flex flex-wrap gap-2">
                {q.options.map((opt) => {
                  const arr = (answers[q.id] as string[]) || [];
                  const selected = arr.includes(opt);
                  return (
                    <button
                      key={opt}
                      onClick={() =>
                        set(q.id, selected ? arr.filter((x) => x !== opt) : [...arr, opt])
                      }
                      className={
                        selected
                          ? "text-xs px-3 py-1.5 rounded-lg border border-blue-300 bg-blue-50 text-blue-700 font-medium"
                          : "text-xs px-3 py-1.5 rounded-lg border border-gray-200 bg-white text-gray-600 hover:bg-gray-50"
                      }
                    >
                      {selected ? "✓ " : ""}{opt}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Submit */}
      <div className="mt-5 flex justify-end">
        <button
          onClick={() => canSubmit && onSubmit(answers)}
          disabled={!canSubmit}
          className={
            canSubmit
              ? "flex items-center gap-1.5 text-xs font-medium px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              : "flex items-center gap-1.5 text-xs font-medium px-4 py-2 bg-gray-100 text-gray-400 rounded-lg cursor-not-allowed"
          }
        >
          <Send className="w-3 h-3" />
          Continue
        </button>
      </div>
    </div>
  );
}
