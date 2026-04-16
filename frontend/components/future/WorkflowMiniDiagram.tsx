"use client";

import clsx from "clsx";
import { ChevronRight } from "lucide-react";

export type StepState = "pending" | "active" | "done";

export type WorkflowStep = {
  label: string;
  state: StepState;
};

const STATE_CLASSES: Record<StepState, string> = {
  pending: "bg-gray-100 text-gray-500 border-gray-200",
  active:  "bg-blue-50 text-blue-700 border-blue-300 ring-1 ring-blue-200",
  done:    "bg-green-50 text-green-700 border-green-300",
};

export default function WorkflowMiniDiagram({ steps }: { steps: WorkflowStep[] }) {
  return (
    <div className="flex items-center flex-wrap gap-y-1.5">
      {steps.map((step, i) => (
        <div key={i} className="flex items-center">
          <span
            className={clsx(
              "text-[11px] font-medium px-2.5 py-1 rounded-full border whitespace-nowrap",
              STATE_CLASSES[step.state],
            )}
          >
            {step.state === "done" && "✓ "}
            {step.label}
          </span>
          {i < steps.length - 1 && (
            <ChevronRight className="w-3.5 h-3.5 text-gray-300 mx-0.5 shrink-0" />
          )}
        </div>
      ))}
    </div>
  );
}
