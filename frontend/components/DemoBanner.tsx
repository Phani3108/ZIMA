"use client";

import { Beaker, ArrowRight, Lightbulb } from "lucide-react";

/**
 * Reusable banner that clearly marks pages as showing demo/preview data.
 * Shows a "How to populate with real data" section with numbered steps.
 *
 * Usage:
 *  <DemoBanner
 *    feature="Workflows"
 *    steps={["Start the backend (docker compose up)", "Create a workflow from Skills Catalog", "Approve stages to see progress"]}
 *  />
 */
export default function DemoBanner({
  feature,
  steps,
  compact = false,
}: {
  feature: string;
  steps: string[];
  compact?: boolean;
}) {
  if (compact) {
    return (
      <div className="mb-4 flex items-center gap-2 bg-violet-50 border border-violet-200 text-violet-700 px-4 py-2 rounded-lg text-sm">
        <Beaker size={14} className="shrink-0" />
        <span>
          <strong>Demo Preview</strong> — Showing sample {feature.toLowerCase()} data. Real data will replace this once the backend is connected.
        </span>
      </div>
    );
  }

  return (
    <div className="mb-6 bg-gradient-to-r from-violet-50 to-blue-50 border border-violet-200 rounded-xl p-5">
      <div className="flex items-start gap-3">
        <div className="p-2 bg-violet-100 rounded-lg shrink-0">
          <Beaker size={18} className="text-violet-600" />
        </div>
        <div className="flex-1">
          <h3 className="font-semibold text-violet-900 text-sm mb-1">
            Demo Preview — {feature}
          </h3>
          <p className="text-sm text-violet-700 mb-3">
            This is sample data showing what you&apos;ll see once the platform is connected. All items below are
            illustrative and will be replaced with your real data.
          </p>
          <div className="flex items-start gap-2">
            <Lightbulb size={14} className="text-violet-500 mt-0.5 shrink-0" />
            <div>
              <p className="text-xs font-medium text-violet-800 mb-1.5">How to populate with real data:</p>
              <ol className="text-xs text-violet-700 space-y-1">
                {steps.map((step, i) => (
                  <li key={i} className="flex items-start gap-1.5">
                    <span className="bg-violet-200 text-violet-800 w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5">
                      {i + 1}
                    </span>
                    {step}
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
