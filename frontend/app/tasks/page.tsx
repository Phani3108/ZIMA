"use client";

import { useState, useEffect, useCallback } from "react";
import {
  ListTodo, Plus, RefreshCw, Loader2, Clock, CheckCircle2,
  XCircle, AlertTriangle, ChevronDown, ArrowUp, ArrowRight, ArrowDown,
} from "lucide-react";
import clsx from "clsx";
import { tasks } from "@/lib/api";
import { useBackend } from "@/lib/useBackend";
import OfflineBanner from "@/components/OfflineBanner";
import DemoBanner from "@/components/DemoBanner";

type Task = {
  id: string;
  title: string;
  description: string;
  status: string;
  priority: number;
  pipeline_name: string | null;
  assignee_agent: string | null;
  routing_rationale: string | null;
  created_at: string;
  updated_at: string;
};

const STATUS_META: Record<string, { label: string; color: string; icon: any }> = {
  queued:     { label: "Queued",      color: "bg-gray-100 text-gray-700",   icon: Clock },
  running:    { label: "Running",     color: "bg-blue-100 text-blue-700",   icon: Loader2 },
  completed:  { label: "Completed",   color: "bg-green-100 text-green-700", icon: CheckCircle2 },
  failed:     { label: "Failed",      color: "bg-red-100 text-red-700",     icon: XCircle },
  cancelled:  { label: "Cancelled",   color: "bg-yellow-100 text-yellow-700", icon: AlertTriangle },
};

const PRIORITY_ICONS: Record<number, { icon: any; label: string; color: string }> = {
  1: { icon: ArrowUp,    label: "High",   color: "text-red-500" },
  2: { icon: ArrowRight, label: "Normal", color: "text-gray-400" },
  3: { icon: ArrowDown,  label: "Low",    color: "text-blue-400" },
};

export default function TasksPage() {
  const { online, checking } = useBackend();
  const [allTasks, setAllTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ title: "", description: "", priority: 2 });

  const load = useCallback(() => {
    if (!online) { setLoading(false); return; }
    setLoading(true);
    tasks.list(filter ?? undefined).then(setAllTasks).catch(() => {}).finally(() => setLoading(false));
  }, [filter, online]);

  useEffect(() => { load(); }, [load]);

  if (!online && !checking) return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2 mb-4"><ListTodo size={22} /> Task Queue</h1>
      <DemoBanner
        feature="Task Queue"
        steps={[
          "Start the backend and click 'New Task' to submit a marketing request",
          "The orchestrator auto-routes tasks to the best-fit agent based on skills",
          "Track status (queued → running → completed) and filter by state",
        ]}
      />
      <div className="flex gap-2 mb-4 flex-wrap">
        {[null, "queued", "running", "completed", "failed"].map((s) => (
          <span key={s ?? "all"}
            className={clsx(
              "px-3 py-1.5 rounded-lg text-xs font-medium border",
              s === null ? "bg-gray-900 text-white border-gray-900" : "bg-white text-gray-600 border-gray-200"
            )}>
            {s ? STATUS_META[s]?.label ?? s : "All"}
          </span>
        ))}
      </div>
      <div className="space-y-3">
        {[
          { id: "t1", title: "Write Q3 blog series outline", description: "Draft 5 blog post outlines targeting product-led growth keywords", status: "completed", priority: 1, pipeline_name: "content_pipeline", assignee_agent: "copywriter", routing_rationale: "SEO + content skill match", created_at: "2026-03-01T10:00:00Z", updated_at: "2026-03-02T14:30:00Z" },
          { id: "t2", title: "Design email header for launch", description: "Create branded header image for v2 launch email", status: "running", priority: 1, pipeline_name: "design_pipeline", assignee_agent: "designer", routing_rationale: "Visual asset request", created_at: "2026-03-10T09:00:00Z", updated_at: "2026-03-10T09:05:00Z" },
          { id: "t3", title: "Competitor social audit", description: "Analyze competitor X social media posting frequency and engagement", status: "queued", priority: 2, pipeline_name: "research_pipeline", assignee_agent: null, routing_rationale: null, created_at: "2026-03-11T08:00:00Z", updated_at: "2026-03-11T08:00:00Z" },
          { id: "t4", title: "Generate LinkedIn post variants", description: "3 LinkedIn post variants for Series A announcement", status: "completed", priority: 2, pipeline_name: "content_pipeline", assignee_agent: "copywriter", routing_rationale: "Copy generation skill", created_at: "2026-03-05T11:00:00Z", updated_at: "2026-03-05T16:00:00Z" },
          { id: "t5", title: "SEMrush keyword refresh", description: "Pull latest keyword rankings and update strategy doc", status: "failed", priority: 3, pipeline_name: "seo_pipeline", assignee_agent: "seo_analyst", routing_rationale: "SEMrush integration skill", created_at: "2026-03-08T07:00:00Z", updated_at: "2026-03-08T07:01:00Z" },
        ].map((task) => {
          const meta = STATUS_META[task.status] || STATUS_META.queued;
          const Icon = meta.icon;
          const prio = PRIORITY_ICONS[task.priority] || PRIORITY_ICONS[2];
          const PrioIcon = prio.icon;
          return (
            <div key={task.id} className="bg-white border rounded-xl p-4">
              <div className="flex items-start gap-3">
                <Icon size={16} className={clsx("mt-0.5 shrink-0", task.status === "running" && "animate-spin")} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-gray-900">{task.title}</h3>
                    <span className={clsx("text-[10px] px-2 py-0.5 rounded-full font-medium", meta.color)}>{meta.label}</span>
                    <PrioIcon size={12} className={prio.color} />
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">{task.description}</p>
                  <div className="flex flex-wrap items-center gap-3 mt-2 text-[11px] text-gray-400">
                    {task.pipeline_name && <span className="bg-gray-50 px-1.5 py-0.5 rounded">{task.pipeline_name}</span>}
                    {task.assignee_agent && <span>Agent: <strong className="text-gray-600">{task.assignee_agent}</strong></span>}
                    {task.routing_rationale && <span className="italic">{task.routing_rationale}</span>}
                    <span>{new Date(task.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );

  const handleCreate = async () => {
    if (!form.title.trim()) return;
    setCreating(true);
    try {
      await tasks.create({ title: form.title, description: form.description, priority: form.priority });
      setForm({ title: "", description: "", priority: 2 });
      setShowCreate(false);
      load();
    } finally { setCreating(false); }
  };

  const handleCancel = async (id: string) => {
    await tasks.cancel(id);
    load();
  };

  const filtered = allTasks;

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <ListTodo size={22} /> Task Queue
          </h1>
          <p className="text-gray-500 text-sm mt-1">Orchestrator task pipeline — create, track, and manage tasks.</p>
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="p-2 rounded-lg border hover:bg-gray-50"><RefreshCw size={16} /></button>
          <button onClick={() => setShowCreate(true)} className="flex items-center gap-1.5 px-3 py-2 bg-brand text-white rounded-lg text-sm font-medium hover:bg-blue-700">
            <Plus size={14} /> New Task
          </button>
        </div>
      </div>

      {/* Status filters */}
      <div className="flex gap-2 mb-6 flex-wrap">
        {[null, "queued", "running", "completed", "failed"].map((s) => (
          <button key={s ?? "all"} onClick={() => setFilter(s)}
            className={clsx(
              "px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors",
              filter === s ? "bg-gray-900 text-white border-gray-900" : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
            )}>
            {s ? STATUS_META[s]?.label ?? s : "All"}
          </button>
        ))}
      </div>

      {/* Create modal */}
      {showCreate && (
        <div className="bg-white border rounded-xl p-5 mb-6 shadow-sm">
          <h3 className="font-semibold mb-3 text-sm">Create Task</h3>
          <input placeholder="Title" value={form.title}
            onChange={(e) => setForm(f => ({ ...f, title: e.target.value }))}
            className="w-full border rounded-lg px-3 py-2 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-brand" />
          <textarea placeholder="Description" value={form.description}
            onChange={(e) => setForm(f => ({ ...f, description: e.target.value }))}
            className="w-full border rounded-lg px-3 py-2 text-sm mb-3 h-20 resize-none focus:outline-none focus:ring-2 focus:ring-brand" />
          <div className="flex items-center gap-3 mb-3">
            <span className="text-xs text-gray-500">Priority:</span>
            {[1, 2, 3].map((p) => {
              const pm = PRIORITY_ICONS[p];
              return (
                <button key={p} onClick={() => setForm(f => ({ ...f, priority: p }))}
                  className={clsx("flex items-center gap-1 px-2 py-1 rounded text-xs border",
                    form.priority === p ? "bg-gray-100 border-gray-400" : "border-gray-200")}>
                  <pm.icon size={12} className={pm.color} /> {pm.label}
                </button>
              );
            })}
          </div>
          <div className="flex gap-2 justify-end">
            <button onClick={() => setShowCreate(false)} className="px-3 py-1.5 text-sm text-gray-500 hover:text-gray-700">Cancel</button>
            <button onClick={handleCreate} disabled={creating || !form.title.trim()}
              className="px-4 py-1.5 bg-brand text-white rounded-lg text-sm font-medium disabled:opacity-50">
              {creating ? "Creating..." : "Create"}
            </button>
          </div>
        </div>
      )}

      {/* Task list */}
      {loading ? (
        <div className="flex justify-center py-20"><Loader2 className="animate-spin text-gray-400" size={24} /></div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20 text-gray-400">No tasks found.</div>
      ) : (
        <div className="space-y-2">
          {filtered.map((t) => {
            const sm = STATUS_META[t.status] ?? STATUS_META.queued;
            const pm = PRIORITY_ICONS[t.priority] ?? PRIORITY_ICONS[2];
            const StatusIcon = sm.icon;
            return (
              <div key={t.id} className="bg-white border rounded-xl p-4 flex items-start gap-4 hover:shadow-sm transition-shadow">
                <div className="mt-0.5">
                  <StatusIcon size={16} className={clsx(t.status === "running" && "animate-spin")} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium text-sm text-gray-900 truncate">{t.title}</span>
                    <span className={clsx("px-2 py-0.5 rounded-full text-[10px] font-medium", sm.color)}>{sm.label}</span>
                    <pm.icon size={12} className={pm.color} />
                  </div>
                  <p className="text-xs text-gray-500 line-clamp-1">{t.description}</p>
                  <div className="flex gap-3 mt-2 text-[11px] text-gray-400">
                    {t.pipeline_name && <span>Pipeline: {t.pipeline_name}</span>}
                    {t.assignee_agent && <span>Agent: {t.assignee_agent}</span>}
                    <span>{new Date(t.created_at).toLocaleString()}</span>
                  </div>
                </div>
                {(t.status === "queued" || t.status === "running") && (
                  <button onClick={() => handleCancel(t.id)}
                    className="text-xs text-red-500 hover:text-red-700 px-2 py-1 border border-red-200 rounded-lg">
                    Cancel
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
