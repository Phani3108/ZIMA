"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import clsx from "clsx";
import {
  ArrowLeft, Save, Loader2, Settings, Image, Ruler,
  Shield, ChevronDown, Check,
} from "lucide-react";
import { designConfig } from "@/lib/api";
import DemoBanner from "@/components/DemoBanner";

/* ─── Types ─────────────────────────────────────────────────────── */

type ToolConfig = {
  skill_id: string;
  primary_tool: string;
  backup_tool: string;
  enabled: boolean;
};

type Preset = {
  skill_id: string;
  platform: string;
  label: string;
  width: number;
  height: number;
  aspect_ratio: string;
  resolution: string;
  format: string;
};

type Rules = {
  max_iterations: number;
  default_quality: string;
  auto_review: boolean;
  auto_approve_min_score: number;
  style_prompt_prefix: string;
};

/* ─── Constants ─────────────────────────────────────────────────── */

const TOOLS = ["gemini", "dalle", "canva", "figma", "midjourney"];
const TOOL_LABELS: Record<string, string> = {
  gemini: "Gemini (Nano Banana 2)",
  dalle: "DALL·E 3",
  canva: "Canva",
  figma: "Figma",
  midjourney: "Midjourney",
};

const SKILL_LABELS: Record<string, string> = {
  social_visual: "Social Media Visual",
  email_header: "Email Header",
  brand_asset: "Brand Asset Pack",
  ad_creative: "Ad Creative",
  presentation_slide: "Presentation Slide",
};

const RESOLUTIONS = ["512", "1K", "2K", "4K"];
const FORMATS = ["png", "jpg", "webp"];
const QUALITIES = ["standard", "hd"];

/* ─── Component ─────────────────────────────────────────────────── */

export default function DesignConfigPage() {
  const [tools, setTools] = useState<ToolConfig[]>([]);
  const [presets, setPresets] = useState<Preset[]>([]);
  const [rules, setRules] = useState<Rules | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);
  const [backendOnline, setBackendOnline] = useState(true);
  const [tab, setTab] = useState<"tools" | "presets" | "rules">("tools");
  const [editingPreset, setEditingPreset] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [t, p, r] = await Promise.all([
        designConfig.getTools(),
        designConfig.getPresets(),
        designConfig.getRules(),
      ]);
      setTools(t);
      setPresets(p);
      setRules(r);
      setBackendOnline(true);
    } catch {
      setBackendOnline(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  /* ── Save handlers ──────────────────────────────────────────── */

  const saveTool = async (tc: ToolConfig) => {
    setSaving(tc.skill_id);
    try {
      await designConfig.putTool(tc);
      await load();
    } finally {
      setSaving(null);
    }
  };

  const savePreset = async (p: Preset) => {
    setSaving(`${p.skill_id}:${p.platform}`);
    try {
      await designConfig.putPreset(p);
      setEditingPreset(null);
      await load();
    } finally {
      setSaving(null);
    }
  };

  const saveRules = async () => {
    if (!rules) return;
    setSaving("rules");
    try {
      await designConfig.putRules(rules);
      await load();
    } finally {
      setSaving(null);
    }
  };

  /* ── Render ─────────────────────────────────────────────────── */

  if (!backendOnline) {
    return (
      <div className="p-8">
        <DemoBanner
          feature="Design Engine Configuration"
          steps={["Start the backend", "Navigate to this page", "Configure tool routing and presets"]}
        />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-8 py-5">
        <div className="flex items-center gap-3 mb-1">
          <Link
            href="/future/agent/design"
            className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <ArrowLeft className="w-4 h-4 text-gray-500" />
          </Link>
          <Settings className="w-5 h-5 text-blue-600" />
          <h1 className="text-xl font-semibold text-gray-900">Engine Configuration</h1>
        </div>
        <p className="text-sm text-gray-500 ml-10">
          Configure tool routing, platform presets, and design rules. Designers will use these settings automatically when invoking skills from Teams.
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 bg-white px-8">
        <nav className="flex gap-6">
          {(["tools", "presets", "rules"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={clsx(
                "py-3 text-sm font-medium border-b-2 transition-colors",
                tab === t
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700",
              )}
            >
              {t === "tools" && <><Image className="w-4 h-4 inline mr-1.5" />Tool Routing</>}
              {t === "presets" && <><Ruler className="w-4 h-4 inline mr-1.5" />Platform Presets</>}
              {t === "rules" && <><Shield className="w-4 h-4 inline mr-1.5" />Rules</>}
            </button>
          ))}
        </nav>
      </div>

      <div className="p-8 max-w-4xl">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
          </div>
        ) : (
          <>
            {/* ── Tool Routing ────────────────────────────────── */}
            {tab === "tools" && (
              <div className="space-y-4">
                <p className="text-sm text-gray-600 mb-4">
                  Set the primary and backup image generation tool for each skill. The engine will try the primary tool first, then fall back to the backup.
                </p>
                {tools.map((tc) => (
                  <div
                    key={tc.skill_id}
                    className="bg-white rounded-xl border border-gray-200 p-5"
                  >
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="font-medium text-gray-900">
                        {SKILL_LABELS[tc.skill_id] || tc.skill_id}
                      </h3>
                      <label className="flex items-center gap-2 text-sm">
                        <input
                          type="checkbox"
                          checked={tc.enabled}
                          onChange={(e) => {
                            const updated = { ...tc, enabled: e.target.checked };
                            setTools((prev) => prev.map((t) => t.skill_id === tc.skill_id ? updated : t));
                          }}
                          className="rounded"
                        />
                        Enabled
                      </label>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-medium text-gray-500 mb-1">
                          Primary Tool
                        </label>
                        <select
                          value={tc.primary_tool}
                          onChange={(e) => {
                            const updated = { ...tc, primary_tool: e.target.value };
                            setTools((prev) => prev.map((t) => t.skill_id === tc.skill_id ? updated : t));
                          }}
                          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                        >
                          {TOOLS.map((tool) => (
                            <option key={tool} value={tool}>
                              {TOOL_LABELS[tool] || tool}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-500 mb-1">
                          Backup Tool
                        </label>
                        <select
                          value={tc.backup_tool}
                          onChange={(e) => {
                            const updated = { ...tc, backup_tool: e.target.value };
                            setTools((prev) => prev.map((t) => t.skill_id === tc.skill_id ? updated : t));
                          }}
                          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                        >
                          {TOOLS.map((tool) => (
                            <option key={tool} value={tool}>
                              {TOOL_LABELS[tool] || tool}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                    <div className="mt-4 flex justify-end">
                      <button
                        onClick={() => saveTool(tc)}
                        disabled={saving === tc.skill_id}
                        className="flex items-center gap-1.5 px-4 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                      >
                        {saving === tc.skill_id ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Save className="w-3.5 h-3.5" />
                        )}
                        Save
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* ── Platform Presets ─────────────────────────────── */}
            {tab === "presets" && (
              <div className="space-y-3">
                <p className="text-sm text-gray-600 mb-4">
                  Image dimensions and format for each platform. These are applied automatically when a designer invokes a skill.
                </p>
                <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        <th className="px-4 py-3">Platform</th>
                        <th className="px-4 py-3">Skill</th>
                        <th className="px-4 py-3">Size</th>
                        <th className="px-4 py-3">Aspect</th>
                        <th className="px-4 py-3">Res</th>
                        <th className="px-4 py-3">Fmt</th>
                        <th className="px-4 py-3 w-20"></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {presets.map((p) => {
                        const key = `${p.skill_id}:${p.platform}`;
                        const isEditing = editingPreset === key;
                        return (
                          <tr key={key} className="hover:bg-gray-50">
                            <td className="px-4 py-2.5 font-medium text-gray-900">
                              {p.label || p.platform}
                            </td>
                            <td className="px-4 py-2.5 text-gray-500">
                              {SKILL_LABELS[p.skill_id] || p.skill_id}
                            </td>
                            <td className="px-4 py-2.5">
                              {isEditing ? (
                                <div className="flex gap-1 items-center">
                                  <input
                                    type="number"
                                    value={p.width}
                                    onChange={(e) => setPresets((prev) => prev.map((pp) => pp === p ? { ...pp, width: parseInt(e.target.value) || 0 } : pp))}
                                    className="w-16 border rounded px-1 py-0.5 text-xs"
                                  />
                                  ×
                                  <input
                                    type="number"
                                    value={p.height}
                                    onChange={(e) => setPresets((prev) => prev.map((pp) => pp === p ? { ...pp, height: parseInt(e.target.value) || 0 } : pp))}
                                    className="w-16 border rounded px-1 py-0.5 text-xs"
                                  />
                                </div>
                              ) : (
                                <span className="text-gray-600">{p.width}×{p.height}</span>
                              )}
                            </td>
                            <td className="px-4 py-2.5 text-gray-600">
                              {isEditing ? (
                                <input
                                  value={p.aspect_ratio}
                                  onChange={(e) => setPresets((prev) => prev.map((pp) => pp === p ? { ...pp, aspect_ratio: e.target.value } : pp))}
                                  className="w-16 border rounded px-1 py-0.5 text-xs"
                                />
                              ) : (
                                p.aspect_ratio
                              )}
                            </td>
                            <td className="px-4 py-2.5">
                              {isEditing ? (
                                <select
                                  value={p.resolution}
                                  onChange={(e) => setPresets((prev) => prev.map((pp) => pp === p ? { ...pp, resolution: e.target.value } : pp))}
                                  className="border rounded px-1 py-0.5 text-xs"
                                >
                                  {RESOLUTIONS.map((r) => <option key={r}>{r}</option>)}
                                </select>
                              ) : (
                                <span className="text-gray-600">{p.resolution}</span>
                              )}
                            </td>
                            <td className="px-4 py-2.5">
                              {isEditing ? (
                                <select
                                  value={p.format}
                                  onChange={(e) => setPresets((prev) => prev.map((pp) => pp === p ? { ...pp, format: e.target.value } : pp))}
                                  className="border rounded px-1 py-0.5 text-xs"
                                >
                                  {FORMATS.map((f) => <option key={f}>{f}</option>)}
                                </select>
                              ) : (
                                <span className="text-gray-500 uppercase text-xs">{p.format}</span>
                              )}
                            </td>
                            <td className="px-4 py-2.5">
                              {isEditing ? (
                                <div className="flex gap-1">
                                  <button
                                    onClick={() => savePreset(p)}
                                    disabled={saving === key}
                                    className="text-blue-600 hover:text-blue-800 text-xs font-medium"
                                  >
                                    {saving === key ? <Loader2 className="w-3 h-3 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                                  </button>
                                  <button
                                    onClick={() => setEditingPreset(null)}
                                    className="text-gray-400 hover:text-gray-600 text-xs"
                                  >
                                    ✕
                                  </button>
                                </div>
                              ) : (
                                <button
                                  onClick={() => setEditingPreset(key)}
                                  className="text-xs text-blue-600 hover:text-blue-800 font-medium"
                                >
                                  Edit
                                </button>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* ── Rules ───────────────────────────────────────── */}
            {tab === "rules" && rules && (
              <div className="space-y-6">
                <p className="text-sm text-gray-600 mb-4">
                  Global design engine rules applied to all skills.
                </p>
                <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
                  <div className="grid grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Max Iterations
                      </label>
                      <input
                        type="number"
                        min={1}
                        max={10}
                        value={rules.max_iterations}
                        onChange={(e) =>
                          setRules({ ...rules, max_iterations: parseInt(e.target.value) || 3 })
                        }
                        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                      />
                      <p className="text-xs text-gray-400 mt-1">
                        How many times a designer can retry/adjust before a new request is needed.
                      </p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Default Quality
                      </label>
                      <select
                        value={rules.default_quality}
                        onChange={(e) => setRules({ ...rules, default_quality: e.target.value })}
                        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                      >
                        {QUALITIES.map((q) => (
                          <option key={q} value={q}>
                            {q === "hd" ? "HD (High Definition)" : "Standard"}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Auto-Approve Min Score
                      </label>
                      <input
                        type="number"
                        min={1}
                        max={10}
                        value={rules.auto_approve_min_score}
                        onChange={(e) =>
                          setRules({ ...rules, auto_approve_min_score: parseInt(e.target.value) || 8 })
                        }
                        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                      />
                      <p className="text-xs text-gray-400 mt-1">
                        Designs scoring above this are auto-approved (when auto-review is on).
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <label className="flex items-center gap-2 text-sm text-gray-700">
                        <input
                          type="checkbox"
                          checked={rules.auto_review}
                          onChange={(e) => setRules({ ...rules, auto_review: e.target.checked })}
                          className="rounded"
                        />
                        Enable auto-review
                      </label>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Style Prompt Prefix
                    </label>
                    <textarea
                      value={rules.style_prompt_prefix}
                      onChange={(e) => setRules({ ...rules, style_prompt_prefix: e.target.value })}
                      placeholder="E.g.: 'Use the Zeta brand palette (blue #003D82, white #FFFFFF). Modern, clean aesthetic.'"
                      rows={3}
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm resize-none"
                    />
                    <p className="text-xs text-gray-400 mt-1">
                      Prepended to every design prompt. Use for brand guidelines, color palette, style directives.
                    </p>
                  </div>
                  <div className="flex justify-end">
                    <button
                      onClick={saveRules}
                      disabled={saving === "rules"}
                      className="flex items-center gap-1.5 px-5 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                    >
                      {saving === "rules" ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Save className="w-4 h-4" />
                      )}
                      Save Rules
                    </button>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
