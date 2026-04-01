"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft, Play, CheckCircle2, Clock, AlertTriangle,
  Loader2, ChevronRight, Target,
} from "lucide-react";
import clsx from "clsx";

type ProgramDetail = {
  id: string;
  name: string;
  description: string;
  campaign_id: string;
  status: string;
  target_date: string | null;
  workflows: any[];
  metrics: {
    total_workflows: number;
    active_workflows: number;
    completed_workflows: number;
    total_stages: number;
    completed_stages: number;
    stuck_stages: number;
    progress_pct: number;
  };
};

export default function ProgramDetailPage() {
  const params = useParams();
  const programId = params.id as string;
  const [program, setProgram] = useState<ProgramDetail | null>(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    fetch(`/api/programs/${programId}`)
      .then((r) => r.json())
      .then((data) => { setProgram(data); setLoading(false); })
      .catch(() => setLoading(false));
  };

  useEffect(() => { load(); }, [programId]);

  const advanceAll = async () => {
    await fetch(`/api/programs/${programId}/advance-all`, { method: "POST" });
    setTimeout(load, 2000);
  };

  if (loading || !program) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="animate-spin text-gray-400" size={24} />
      </div>
    );
  }

  const m = program.metrics;

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <Link href="/programs" className="flex items-center gap-1 text-sm text-gray-500 hover:text-brand mb-4">
        <ArrowLeft size={14} /> Back to Programs
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">{program.name}</h1>
          {program.description && <p className="text-gray-500 mt-1 text-sm">{program.description}</p>}
          <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
            <span>Campaign: {program.campaign_id.slice(0, 8)}...</span>
            {program.target_date && (
              <span className="flex items-center gap-1">
                <Target size={10} /> Due: {new Date(program.target_date).toLocaleDateString()}
              </span>
            )}
          </div>
        </div>
        <button
          onClick={advanceAll}
          className="flex items-center gap-1 bg-brand text-white px-3 py-2 rounded-lg text-sm hover:bg-blue-700"
        >
          <Play size={12} /> Advance All
        </button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white border rounded-xl p-4">
          <p className="text-[11px] text-gray-500 uppercase">Progress</p>
          <p className="text-2xl font-bold text-brand">{m.progress_pct}%</p>
          <div className="bg-gray-100 rounded-full h-1.5 mt-2 overflow-hidden">
            <div className="bg-brand h-full rounded-full" style={{ width: `${m.progress_pct}%` }} />
          </div>
        </div>
        <div className="bg-white border rounded-xl p-4">
          <p className="text-[11px] text-gray-500 uppercase">Workflows</p>
          <p className="text-2xl font-bold text-gray-900">{m.total_workflows}</p>
          <p className="text-xs text-gray-400">{m.active_workflows} active, {m.completed_workflows} done</p>
        </div>
        <div className="bg-white border rounded-xl p-4">
          <p className="text-[11px] text-gray-500 uppercase">Stages</p>
          <p className="text-2xl font-bold text-gray-900">{m.completed_stages}/{m.total_stages}</p>
          <p className="text-xs text-gray-400">completed</p>
        </div>
        <div className="bg-white border rounded-xl p-4">
          <p className="text-[11px] text-gray-500 uppercase">Stuck</p>
          <p className={clsx("text-2xl font-bold", m.stuck_stages > 0 ? "text-red-500" : "text-green-500")}>
            {m.stuck_stages}
          </p>
          <p className="text-xs text-gray-400">need attention</p>
        </div>
      </div>

      {/* Workflow list */}
      <h2 className="text-sm font-semibold text-gray-700 mb-3">Workflows ({program.workflows.length})</h2>
      <div className="space-y-3">
        {program.workflows.map((wf: any) => {
          const completed = wf.stages?.filter((s: any) => s.status === "approved").length || 0;
          const total = wf.stages?.length || 0;
          const pct = total > 0 ? Math.round((completed / total) * 100) : 0;

          return (
            <Link
              key={wf.id}
              href={`/workflows/${wf.id}`}
              className="flex items-center gap-4 bg-white border rounded-xl p-4 hover:shadow-sm transition-shadow group"
            >
              <div className="flex-1 min-w-0">
                <h4 className="font-medium text-sm text-gray-900">{wf.name}</h4>
                <div className="flex items-center gap-2 mt-1">
                  <div className="flex gap-0.5 flex-1">
                    {(wf.stages || []).map((s: any) => (
                      <div
                        key={s.id}
                        className={clsx("h-1.5 rounded-full flex-1",
                          s.status === "approved" ? "bg-green-500" :
                          s.status === "in_progress" ? "bg-blue-500 animate-pulse" :
                          s.status === "awaiting_review" ? "bg-amber-400" :
                          s.status === "needs_retry" ? "bg-red-400" :
                          "bg-gray-200"
                        )}
                      />
                    ))}
                  </div>
                  <span className="text-xs text-gray-500 shrink-0">{pct}%</span>
                </div>
              </div>
              <span className={clsx("text-xs px-2 py-0.5 rounded-full",
                wf.status === "active" ? "bg-blue-50 text-blue-600" :
                wf.status === "completed" ? "bg-green-50 text-green-600" :
                "bg-gray-50 text-gray-500"
              )}>
                {wf.status}
              </span>
              <ChevronRight size={14} className="text-gray-300 group-hover:text-brand" />
            </Link>
          );
        })}
      </div>
    </div>
  );
}
