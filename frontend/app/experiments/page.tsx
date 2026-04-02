"use client";

import { useState, useEffect, useCallback } from "react";
import {
  FlaskConical, Plus, RefreshCw, Loader2, Play, Trophy,
  BarChart3, Star,
} from "lucide-react";
import clsx from "clsx";
import { experiments } from "@/lib/api";
import { useBackend } from "@/lib/useBackend";
import OfflineBanner from "@/components/OfflineBanner";
import DemoBanner from "@/components/DemoBanner";

type Variant = {
  variant_id: string;
  variant_label: string;
  llm_used: string | null;
  prompt_variation: string | null;
  output: string | null;
  score: number | null;
  feedback: string;
  is_winner: boolean;
};

type Experiment = {
  id: string;
  name: string;
  brief: string;
  status: string;
  variants: Variant[];
  skill_id: string | null;
  campaign_id: string | null;
  created_at: string;
  concluded_at: string | null;
};

const STATUS_COLORS: Record<string, string> = {
  draft:     "bg-gray-100 text-gray-700",
  running:   "bg-blue-100 text-blue-700",
  scoring:   "bg-amber-100 text-amber-700",
  concluded: "bg-green-100 text-green-700",
};

export default function ExperimentsPage() {
  const { online, checking } = useBackend();
  const [items, setItems] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Experiment | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({
    name: "", brief: "",
    variants: [{ variant_label: "A", llm_used: "" }, { variant_label: "B", llm_used: "" }],
  });

  const load = useCallback(() => {
    if (!online) { setLoading(false); return; }
    setLoading(true);
    experiments.list().then(setItems).catch(() => {}).finally(() => setLoading(false));
  }, [online]);

  useEffect(() => { load(); }, [load]);

  if (!online && !checking) return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2 mb-4"><FlaskConical size={22} /> A/B Experiments</h1>
      <DemoBanner
        feature="A/B Experiments"
        steps={[
          "Start the backend and click 'New Experiment' — define a brief and 2+ variants",
          "Run the experiment to generate outputs from different LLMs or prompts",
          "Score each variant and conclude — the winner is auto-highlighted",
        ]}
      />
      <div className="space-y-4">
        {[
          { id: "e1", name: "LinkedIn CTA Test", brief: "Compare casual vs. formal CTA on Series A post", status: "concluded", created_at: "2026-02-15T10:00:00Z", concluded_at: "2026-02-16T14:00:00Z", variants: [
            { variant_id: "v1", variant_label: "A — Casual", llm_used: "gpt-4o", output: "\"We just raised $12M to change marketing forever. Join the ride 🚀\"", score: 8.2, feedback: "Engaging but slightly informal for investors", is_winner: true },
            { variant_id: "v2", variant_label: "B — Formal", llm_used: "gpt-4o", output: "\"Zeta announces $12M Series A to accelerate AI-driven marketing innovation.\"", score: 7.5, feedback: "Professional but lower engagement predicted", is_winner: false },
          ] },
          { id: "e2", name: "Email Subject Line", brief: "Test urgency vs. curiosity subject lines for trial-to-paid email", status: "running", created_at: "2026-03-10T09:00:00Z", concluded_at: null, variants: [
            { variant_id: "v3", variant_label: "A — Urgency", llm_used: "gpt-4o-mini", output: "\"Your trial ends tomorrow — don't lose your campaigns\"", score: null, feedback: "", is_winner: false },
            { variant_id: "v4", variant_label: "B — Curiosity", llm_used: "claude-3-sonnet", output: "\"Here's what 14 days of AI marketing actually built for you\"", score: null, feedback: "", is_winner: false },
          ] },
          { id: "e3", name: "Blog Intro Hook", brief: "Stat-led vs. question-led blog opening", status: "draft", created_at: "2026-03-11T08:00:00Z", concluded_at: null, variants: [
            { variant_id: "v5", variant_label: "A — Stat", llm_used: "", output: null, score: null, feedback: "", is_winner: false },
            { variant_id: "v6", variant_label: "B — Question", llm_used: "", output: null, score: null, feedback: "", is_winner: false },
          ] },
        ].map((exp) => (
          <div key={exp.id} className="bg-white border rounded-xl p-5">
            <div className="flex items-center justify-between mb-2">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold text-gray-900 text-sm">{exp.name}</h3>
                  <span className={clsx("text-[10px] px-2 py-0.5 rounded-full font-medium", STATUS_COLORS[exp.status] || "bg-gray-100 text-gray-600")}>{exp.status}</span>
                </div>
                <p className="text-xs text-gray-500 mt-0.5">{exp.brief}</p>
              </div>
              <span className="text-[10px] text-gray-400">{new Date(exp.created_at).toLocaleDateString()}</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
              {exp.variants.map((v) => (
                <div key={v.variant_id} className={clsx("border rounded-lg p-3", v.is_winner ? "border-green-300 bg-green-50" : "border-gray-100")}>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-semibold text-gray-700">{v.variant_label}</span>
                    {v.is_winner && <Trophy size={12} className="text-green-600" />}
                    {v.llm_used && <span className="text-[10px] text-gray-400 font-mono">{v.llm_used}</span>}
                  </div>
                  {v.output && <p className="text-xs text-gray-600 mb-1 italic">{v.output}</p>}
                  <div className="flex items-center gap-3 text-[11px] text-gray-400">
                    {v.score !== null && <span className="flex items-center gap-1"><Star size={10} className="text-amber-500" /> {v.score}/10</span>}
                    {v.feedback && <span>{v.feedback}</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const handleCreate = async () => {
    if (!form.name.trim() || !form.brief.trim()) return;
    setCreating(true);
    try {
      const created = await experiments.create({
        name: form.name,
        brief: form.brief,
        variants: form.variants.map(v => ({
          variant_label: v.variant_label,
          llm_used: v.llm_used || undefined,
        })),
      });
      setShowCreate(false);
      setForm({ name: "", brief: "", variants: [{ variant_label: "A", llm_used: "" }, { variant_label: "B", llm_used: "" }] });
      load();
    } finally { setCreating(false); }
  };

  const handleRun = async (id: string) => {
    await experiments.run(id);
    load();
  };

  const handleScore = async (expId: string, variantId: string, score: number) => {
    await experiments.score(expId, { variant_id: variantId, score });
    // Refresh details
    const updated = await experiments.get(expId);
    setSelected(updated);
    load();
  };

  const handleConclude = async (id: string) => {
    await experiments.conclude(id);
    const updated = await experiments.get(id);
    setSelected(updated);
    load();
  };

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <FlaskConical size={22} /> A/B Experiments
          </h1>
          <p className="text-gray-500 text-sm mt-1">Test content variants side-by-side and pick the winner.</p>
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="p-2 rounded-lg border hover:bg-gray-50"><RefreshCw size={16} /></button>
          <button onClick={() => setShowCreate(true)}
            className="flex items-center gap-1.5 px-3 py-2 bg-brand text-white rounded-lg text-sm font-medium hover:bg-blue-700">
            <Plus size={14} /> New Experiment
          </button>
        </div>
      </div>

      {showCreate && (
        <div className="bg-white border rounded-xl p-5 mb-6 shadow-sm">
          <h3 className="font-semibold mb-3 text-sm">Create Experiment</h3>
          <input placeholder="Experiment name" value={form.name}
            onChange={(e) => setForm(f => ({ ...f, name: e.target.value }))}
            className="w-full border rounded-lg px-3 py-2 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-brand" />
          <textarea placeholder="Brief / prompt to test" value={form.brief}
            onChange={(e) => setForm(f => ({ ...f, brief: e.target.value }))}
            className="w-full border rounded-lg px-3 py-2 text-sm mb-3 h-20 resize-none focus:outline-none focus:ring-2 focus:ring-brand" />
          <div className="space-y-2 mb-3">
            <span className="text-xs text-gray-500 font-medium">Variants</span>
            {form.variants.map((v, i) => (
              <div key={i} className="flex gap-2">
                <input placeholder="Label" value={v.variant_label}
                  onChange={(e) => { const vs = [...form.variants]; vs[i] = { ...vs[i], variant_label: e.target.value }; setForm(f => ({ ...f, variants: vs })); }}
                  className="border rounded-lg px-3 py-2 text-sm w-32 focus:outline-none focus:ring-2 focus:ring-brand" />
                <input placeholder="LLM (optional)" value={v.llm_used}
                  onChange={(e) => { const vs = [...form.variants]; vs[i] = { ...vs[i], llm_used: e.target.value }; setForm(f => ({ ...f, variants: vs })); }}
                  className="border rounded-lg px-3 py-2 text-sm flex-1 focus:outline-none focus:ring-2 focus:ring-brand" />
              </div>
            ))}
            <button onClick={() => setForm(f => ({ ...f, variants: [...f.variants, { variant_label: String.fromCharCode(65 + f.variants.length), llm_used: "" }] }))}
              className="text-xs text-brand hover:underline">+ Add variant</button>
          </div>
          <div className="flex gap-2 justify-end">
            <button onClick={() => setShowCreate(false)} className="px-3 py-1.5 text-sm text-gray-500">Cancel</button>
            <button onClick={handleCreate} disabled={creating || !form.name.trim() || !form.brief.trim()}
              className="px-4 py-1.5 bg-brand text-white rounded-lg text-sm font-medium disabled:opacity-50">
              {creating ? "Creating..." : "Create"}
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Experiment list */}
        <div className="lg:col-span-1 space-y-2">
          {loading ? (
            <div className="flex justify-center py-10"><Loader2 className="animate-spin text-gray-400" size={20} /></div>
          ) : items.length === 0 ? (
            <div className="text-center py-10 text-gray-400 text-sm">No experiments yet.</div>
          ) : items.map((e) => (
            <button key={e.id} onClick={() => setSelected(e)}
              className={clsx("w-full text-left bg-white border rounded-xl p-4 hover:shadow-sm transition-shadow",
                selected?.id === e.id && "ring-2 ring-brand")}>
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-sm text-gray-900 truncate">{e.name}</span>
                <span className={clsx("px-2 py-0.5 rounded-full text-[10px] font-medium", STATUS_COLORS[e.status] ?? STATUS_COLORS.draft)}>
                  {e.status}
                </span>
              </div>
              <p className="text-xs text-gray-500 line-clamp-2">{e.brief}</p>
              <span className="text-[11px] text-gray-400 mt-1 block">{e.variants.length} variants</span>
            </button>
          ))}
        </div>

        {/* Detail */}
        <div className="lg:col-span-2">
          {selected ? (
            <div className="bg-white border rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-900">{selected.name}</h3>
                <div className="flex gap-2">
                  {selected.status === "draft" && (
                    <button onClick={() => handleRun(selected.id)}
                      className="flex items-center gap-1 px-3 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-medium hover:bg-blue-700">
                      <Play size={12} /> Run All Variants
                    </button>
                  )}
                  {selected.status === "scoring" && (
                    <button onClick={() => handleConclude(selected.id)}
                      className="flex items-center gap-1 px-3 py-1.5 bg-green-600 text-white rounded-lg text-xs font-medium hover:bg-green-700">
                      <Trophy size={12} /> Conclude
                    </button>
                  )}
                </div>
              </div>
              <p className="text-sm text-gray-500 mb-4">{selected.brief}</p>
              <div className="space-y-4">
                {selected.variants.map((v) => (
                  <div key={v.variant_id} className={clsx("border rounded-lg p-4", v.is_winner && "ring-2 ring-green-500 bg-green-50")}>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm">{v.variant_label}</span>
                        {v.llm_used && <code className="text-[11px] bg-gray-100 px-1.5 py-0.5 rounded">{v.llm_used}</code>}
                        {v.is_winner && <Trophy size={14} className="text-green-600" />}
                      </div>
                      {v.score !== null && (
                        <span className="flex items-center gap-1 text-sm font-medium text-amber-600">
                          <Star size={14} /> {v.score.toFixed(1)}
                        </span>
                      )}
                    </div>
                    {v.output ? (
                      <pre className="bg-gray-50 rounded-lg p-3 text-xs whitespace-pre-wrap max-h-40 overflow-auto">{v.output}</pre>
                    ) : (
                      <p className="text-xs text-gray-400 italic">Not yet generated</p>
                    )}
                    {selected.status === "scoring" && v.output && (
                      <div className="flex gap-1 mt-3">
                        {[1, 2, 3, 4, 5].map((s) => (
                          <button key={s} onClick={() => handleScore(selected.id, v.variant_id, s)}
                            className={clsx("w-8 h-8 rounded-lg border text-xs font-medium transition-colors",
                              v.score === s ? "bg-amber-100 border-amber-400 text-amber-700" : "hover:bg-gray-50")}>
                            {s}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center py-20 text-gray-400 text-sm">
              Select an experiment to view details.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
