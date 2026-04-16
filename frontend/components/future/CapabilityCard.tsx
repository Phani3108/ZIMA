"use client";

import WorkflowMiniDiagram, { type WorkflowStep } from "./WorkflowMiniDiagram";
import { Play } from "lucide-react";

export type Capability = {
  id: string;
  title: string;
  description: string;
  steps: WorkflowStep[];
  tools: string[];         // tag labels like "Gemini", "Canva"
};

type Props = {
  capability: Capability;
  onStart: (capabilityId: string) => void;
};

export default function CapabilityCard({ capability, onStart }: Props) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 flex flex-col gap-3.5 hover:shadow-md transition-shadow group">
      {/* Title */}
      <div>
        <h4 className="text-sm font-semibold text-gray-800">{capability.title}</h4>
        <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">{capability.description}</p>
      </div>

      {/* Workflow diagram */}
      <WorkflowMiniDiagram steps={capability.steps} />

      {/* Footer: tool tags + start button */}
      <div className="flex items-center justify-between pt-1 border-t border-gray-100">
        <div className="flex gap-1.5 flex-wrap">
          {capability.tools.map((t) => (
            <span
              key={t}
              className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-600"
            >
              {t}
            </span>
          ))}
        </div>
        <button
          onClick={() => onStart(capability.id)}
          className="flex items-center gap-1.5 text-xs font-medium text-blue-600 hover:text-white hover:bg-blue-600 px-3 py-1.5 rounded-lg border border-blue-200 hover:border-blue-600 transition-all"
        >
          <Play className="w-3 h-3" />
          Start Task
        </button>
      </div>
    </div>
  );
}
