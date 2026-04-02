"use client";

import { useState, useEffect, useCallback } from "react";
import {
  CalendarClock, Plus, RefreshCw, Loader2, Play, Pause,
  Trash2, Clock, CheckCircle2,
} from "lucide-react";
import clsx from "clsx";
import { schedules, workflows } from "@/lib/api";
import { useBackend } from "@/lib/useBackend";
import OfflineBanner from "@/components/OfflineBanner";
import DemoBanner from "@/components/DemoBanner";

type Schedule = {
  id: string;
  name: string;
  cron_expr: string;
  template_id: string;
  variables: Record<string, any>;
  enabled: boolean;
  run_count: number;
  max_runs: number;
  last_run_at: string | null;
  next_run_at: string | null;
  created_at: string;
};

type Template = { id: string; name: string; description: string };

export default function SchedulesPage() {
  const { online, checking } = useBackend();
  const [items, setItems] = useState<Schedule[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ name: "", cron_expr: "0 9 * * 1", template_id: "", max_runs: 0 });

  const load = useCallback(() => {
    if (!online) { setLoading(false); return; }
    setLoading(true);
    Promise.all([schedules.list(), workflows.templates()])
      .then(([s, t]) => { setItems(s); setTemplates(t); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [online]);

  useEffect(() => { load(); }, [load]);

  if (!online && !checking) return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2 mb-4"><CalendarClock size={22} /> Schedules</h1>
      <DemoBanner
        feature="Schedules"
        steps={[
          "Start the backend and click 'New Schedule' to pick a workflow template",
          "Set a cron expression (e.g. '0 9 * * 1' for every Monday at 9 AM)",
          "Enable/disable schedules and track run count, last run, and next trigger",
        ]}
      />
      <div className="space-y-3">
        {[
          { id: "s1", name: "Weekly Blog Roundup", cron_expr: "0 9 * * 1", template_id: "tpl-blog", enabled: true, run_count: 12, max_runs: 0, last_run_at: "2026-03-10T09:00:00Z", next_run_at: "2026-03-17T09:00:00Z", created_at: "2026-01-06T10:00:00Z" },
          { id: "s2", name: "Daily Social Post", cron_expr: "0 8 * * *", template_id: "tpl-social", enabled: true, run_count: 45, max_runs: 0, last_run_at: "2026-03-11T08:00:00Z", next_run_at: "2026-03-12T08:00:00Z", created_at: "2026-01-20T08:00:00Z" },
          { id: "s3", name: "Monthly SEO Audit", cron_expr: "0 6 1 * *", template_id: "tpl-seo", enabled: true, run_count: 3, max_runs: 12, last_run_at: "2026-03-01T06:00:00Z", next_run_at: "2026-04-01T06:00:00Z", created_at: "2026-01-01T06:00:00Z" },
          { id: "s4", name: "Quarterly Competitor Report", cron_expr: "0 10 1 */3 *", template_id: "tpl-competitor", enabled: false, run_count: 1, max_runs: 4, last_run_at: "2026-01-01T10:00:00Z", next_run_at: null, created_at: "2025-12-15T10:00:00Z" },
        ].map((sched) => (
          <div key={sched.id} className="bg-white border rounded-xl p-4 flex items-center gap-4">
            <div className={clsx("w-3 h-3 rounded-full shrink-0", sched.enabled ? "bg-green-400" : "bg-gray-300")} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-semibold text-gray-900">{sched.name}</h3>
                <code className="text-[10px] bg-gray-100 px-1.5 py-0.5 rounded font-mono text-gray-500">{sched.cron_expr}</code>
                {!sched.enabled && <span className="text-[10px] px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">Paused</span>}
              </div>
              <div className="flex items-center gap-4 mt-1 text-[11px] text-gray-400">
                <span className="flex items-center gap-1"><CheckCircle2 size={10} /> {sched.run_count} runs{sched.max_runs > 0 ? ` / ${sched.max_runs} max` : ""}</span>
                {sched.last_run_at && <span className="flex items-center gap-1"><Clock size={10} /> Last: {new Date(sched.last_run_at).toLocaleDateString()}</span>}
                {sched.next_run_at && <span className="flex items-center gap-1"><Play size={10} /> Next: {new Date(sched.next_run_at).toLocaleDateString()}</span>}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const handleCreate = async () => {
    if (!form.name.trim() || !form.cron_expr.trim() || !form.template_id) return;
    setCreating(true);
    try {
      await schedules.create({
        name: form.name,
        cron_expr: form.cron_expr,
        template_id: form.template_id,
        max_runs: form.max_runs,
      });
      setForm({ name: "", cron_expr: "0 9 * * 1", template_id: "", max_runs: 0 });
      setShowCreate(false);
      load();
    } finally { setCreating(false); }
  };

  const handleToggle = async (id: string, current: boolean) => {
    await schedules.toggle(id, !current);
    load();
  };

  const handleDelete = async (id: string) => {
    await schedules.delete(id);
    load();
  };

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <CalendarClock size={22} /> Schedules
          </h1>
          <p className="text-gray-500 text-sm mt-1">Recurring workflow triggers with cron expressions.</p>
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="p-2 rounded-lg border hover:bg-gray-50"><RefreshCw size={16} /></button>
          <button onClick={() => setShowCreate(true)}
            className="flex items-center gap-1.5 px-3 py-2 bg-brand text-white rounded-lg text-sm font-medium hover:bg-blue-700">
            <Plus size={14} /> New Schedule
          </button>
        </div>
      </div>

      {showCreate && (
        <div className="bg-white border rounded-xl p-5 mb-6 shadow-sm">
          <h3 className="font-semibold mb-3 text-sm">Create Schedule</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
            <input placeholder="Name" value={form.name}
              onChange={(e) => setForm(f => ({ ...f, name: e.target.value }))}
              className="border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand" />
            <input placeholder="Cron (e.g. 0 9 * * 1)" value={form.cron_expr}
              onChange={(e) => setForm(f => ({ ...f, cron_expr: e.target.value }))}
              className="border rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand" />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
            <select value={form.template_id}
              onChange={(e) => setForm(f => ({ ...f, template_id: e.target.value }))}
              className="border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand">
              <option value="">Select template...</option>
              {templates.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
            <input type="number" placeholder="Max runs (0=unlimited)" value={form.max_runs}
              onChange={(e) => setForm(f => ({ ...f, max_runs: parseInt(e.target.value) || 0 }))}
              className="border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand" />
          </div>
          <div className="flex gap-2 justify-end">
            <button onClick={() => setShowCreate(false)} className="px-3 py-1.5 text-sm text-gray-500">Cancel</button>
            <button onClick={handleCreate} disabled={creating || !form.name.trim() || !form.template_id}
              className="px-4 py-1.5 bg-brand text-white rounded-lg text-sm font-medium disabled:opacity-50">
              {creating ? "Creating..." : "Create"}
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-20"><Loader2 className="animate-spin text-gray-400" size={24} /></div>
      ) : items.length === 0 ? (
        <div className="text-center py-20 text-gray-400">No schedules configured.</div>
      ) : (
        <div className="space-y-2">
          {items.map((s) => (
            <div key={s.id} className="bg-white border rounded-xl p-4 flex items-center gap-4 hover:shadow-sm transition-shadow">
              <div className={clsx("w-2 h-2 rounded-full", s.enabled ? "bg-green-500" : "bg-gray-300")} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium text-sm text-gray-900">{s.name}</span>
                  <code className="text-[11px] bg-gray-100 px-1.5 py-0.5 rounded text-gray-600">{s.cron_expr}</code>
                </div>
                <div className="flex gap-4 text-[11px] text-gray-400">
                  <span>Template: {s.template_id}</span>
                  <span>Runs: {s.run_count}{s.max_runs > 0 ? `/${s.max_runs}` : ""}</span>
                  {s.next_run_at && <span>Next: {new Date(s.next_run_at).toLocaleString()}</span>}
                </div>
              </div>
              <button onClick={() => handleToggle(s.id, s.enabled)}
                className={clsx("p-2 rounded-lg border text-xs", s.enabled ? "text-yellow-600 border-yellow-200 hover:bg-yellow-50" : "text-green-600 border-green-200 hover:bg-green-50")}>
                {s.enabled ? <Pause size={14} /> : <Play size={14} />}
              </button>
              <button onClick={() => handleDelete(s.id)} className="p-2 rounded-lg border text-red-400 border-red-200 hover:bg-red-50">
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
