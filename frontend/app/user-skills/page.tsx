"use client";

import { useState, useEffect, useCallback } from "react";
import { Code2, Plus, Play, Trash2, RefreshCw, Loader2, CheckCircle2, XCircle, Share2 } from "lucide-react";
import clsx from "clsx";
import { userSkills } from "@/lib/api";

type Skill = {
  id: string;
  name: string;
  description: string;
  code: string;
  is_shared: boolean;
  tags: string[];
  created_by: string;
  created_at: string;
};

type ExecResult = { output: any; error: string | null; elapsed_ms: number } | null;

export default function UserSkillsPage() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Skill | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [execResult, setExecResult] = useState<ExecResult>(null);
  const [executing, setExecuting] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validationMsg, setValidationMsg] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", code: "", is_shared: false, tags: "" });

  const load = useCallback(() => {
    setLoading(true);
    userSkills.list().then(setSkills).catch(() => {}).finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async () => {
    if (!form.name.trim() || !form.code.trim()) return;
    setCreating(true);
    try {
      await userSkills.create({
        name: form.name,
        description: form.description,
        code: form.code,
        is_shared: form.is_shared,
        tags: form.tags.split(",").map(s => s.trim()).filter(Boolean),
      });
      setForm({ name: "", description: "", code: "", is_shared: false, tags: "" });
      setShowCreate(false);
      load();
    } finally { setCreating(false); }
  };

  const handleValidate = async () => {
    setValidating(true);
    setValidationMsg(null);
    try {
      const res = await userSkills.validate(form.code || selected?.code || "");
      setValidationMsg(res.valid ? "✓ Code is valid" : `✗ ${res.error}`);
    } catch { setValidationMsg("✗ Validation failed"); }
    finally { setValidating(false); }
  };

  const handleExecute = async (id: string) => {
    setExecuting(true);
    setExecResult(null);
    try {
      const res = await userSkills.execute(id);
      setExecResult(res);
    } catch (e: any) { setExecResult({ output: null, error: e.message, elapsed_ms: 0 }); }
    finally { setExecuting(false); }
  };

  const handleDelete = async (id: string) => {
    await userSkills.delete(id);
    if (selected?.id === id) setSelected(null);
    load();
  };

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Code2 size={22} /> User Skills
          </h1>
          <p className="text-gray-500 text-sm mt-1">Create and run custom codable skills in a sandboxed environment.</p>
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="p-2 rounded-lg border hover:bg-gray-50"><RefreshCw size={16} /></button>
          <button onClick={() => { setShowCreate(true); setSelected(null); }}
            className="flex items-center gap-1.5 px-3 py-2 bg-brand text-white rounded-lg text-sm font-medium hover:bg-blue-700">
            <Plus size={14} /> New Skill
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Skill list */}
        <div className="lg:col-span-1 space-y-2">
          {loading ? (
            <div className="flex justify-center py-10"><Loader2 className="animate-spin text-gray-400" size={20} /></div>
          ) : skills.length === 0 ? (
            <div className="text-center py-10 text-gray-400 text-sm">No user skills yet.</div>
          ) : skills.map((s) => (
            <button key={s.id} onClick={() => { setSelected(s); setShowCreate(false); setExecResult(null); }}
              className={clsx("w-full text-left bg-white border rounded-xl p-4 hover:shadow-sm transition-shadow",
                selected?.id === s.id && "ring-2 ring-brand")}>
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-sm text-gray-900">{s.name}</span>
                {s.is_shared && <Share2 size={12} className="text-green-500" />}
              </div>
              <p className="text-xs text-gray-500 line-clamp-2">{s.description || "No description"}</p>
              {s.tags.length > 0 && (
                <div className="flex gap-1 mt-2 flex-wrap">
                  {s.tags.map(t => <span key={t} className="px-1.5 py-0.5 bg-gray-100 text-[10px] text-gray-500 rounded">{t}</span>)}
                </div>
              )}
            </button>
          ))}
        </div>

        {/* Detail / Create panel */}
        <div className="lg:col-span-2">
          {showCreate ? (
            <div className="bg-white border rounded-xl p-6">
              <h3 className="font-semibold mb-4">Create Skill</h3>
              <input placeholder="Name" value={form.name}
                onChange={(e) => setForm(f => ({ ...f, name: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-brand" />
              <input placeholder="Description" value={form.description}
                onChange={(e) => setForm(f => ({ ...f, description: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-brand" />
              <textarea placeholder="Python code..." value={form.code}
                onChange={(e) => setForm(f => ({ ...f, code: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm mb-3 h-48 font-mono text-xs resize-none focus:outline-none focus:ring-2 focus:ring-brand" />
              <input placeholder="Tags (comma-separated)" value={form.tags}
                onChange={(e) => setForm(f => ({ ...f, tags: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-brand" />
              <label className="flex items-center gap-2 mb-4 text-sm text-gray-600">
                <input type="checkbox" checked={form.is_shared}
                  onChange={(e) => setForm(f => ({ ...f, is_shared: e.target.checked }))} />
                Share with team
              </label>
              {validationMsg && (
                <div className={clsx("text-xs mb-3 px-3 py-2 rounded-lg",
                  validationMsg.startsWith("✓") ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700")}>
                  {validationMsg}
                </div>
              )}
              <div className="flex gap-2 justify-end">
                <button onClick={handleValidate} disabled={validating || !form.code.trim()}
                  className="px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50 disabled:opacity-50">
                  {validating ? "Checking..." : "Validate"}
                </button>
                <button onClick={() => setShowCreate(false)} className="px-3 py-1.5 text-sm text-gray-500 hover:text-gray-700">Cancel</button>
                <button onClick={handleCreate} disabled={creating || !form.name.trim() || !form.code.trim()}
                  className="px-4 py-1.5 bg-brand text-white rounded-lg text-sm font-medium disabled:opacity-50">
                  {creating ? "Creating..." : "Create"}
                </button>
              </div>
            </div>
          ) : selected ? (
            <div className="bg-white border rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-900">{selected.name}</h3>
                <div className="flex gap-2">
                  <button onClick={() => handleExecute(selected.id)} disabled={executing}
                    className="flex items-center gap-1 px-3 py-1.5 bg-green-600 text-white rounded-lg text-xs font-medium hover:bg-green-700 disabled:opacity-50">
                    {executing ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />} Run
                  </button>
                  <button onClick={() => handleDelete(selected.id)}
                    className="flex items-center gap-1 px-3 py-1.5 text-red-500 border border-red-200 rounded-lg text-xs hover:bg-red-50">
                    <Trash2 size={12} /> Delete
                  </button>
                </div>
              </div>
              <p className="text-sm text-gray-500 mb-4">{selected.description || "No description"}</p>
              <pre className="bg-gray-50 border rounded-lg p-4 text-xs font-mono overflow-auto max-h-64 mb-4">{selected.code}</pre>
              {execResult && (
                <div className={clsx("rounded-lg p-4 text-xs", execResult.error ? "bg-red-50" : "bg-green-50")}>
                  <div className="font-medium mb-1">{execResult.error ? "Error" : `Output (${execResult.elapsed_ms}ms)`}</div>
                  <pre className="whitespace-pre-wrap">{execResult.error || JSON.stringify(execResult.output, null, 2)}</pre>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center py-20 text-gray-400 text-sm">
              Select a skill or create a new one.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
