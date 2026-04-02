"use client";

import { useState, useEffect } from "react";
import {
  GitBranch, Plus, ArrowRight, Settings2, Play, Pause,
  CheckCircle2, XCircle, Clock, Loader2, Zap, Trash2,
  ChevronDown, ChevronUp,
} from "lucide-react";
import clsx from "clsx";
import { handoffs, teams, workflows } from "@/lib/api";
import { useBackend } from "@/lib/useBackend";
import OfflineBanner from "@/components/OfflineBanner";

type Rule = {
  id: string;
  name: string;
  source_team_id: string;
  trigger_skill_id: string | null;
  trigger_event: string;
  target_team_id: string;
  target_template_id: string;
  variable_mapping: Record<string, string>;
  auto_start: boolean;
  enabled: boolean;
  created_at: string;
};

type LogEntry = {
  id: string;
  rule_id: string;
  source_workflow_id: string;
  target_workflow_id: string | null;
  status: string;
  error: string | null;
  created_at: string;
};

const STATIC_RULES: Rule[] = [
  {
    id: "hnd-demo-1", name: "SEO Brief → Blog Post", source_team_id: "seo-team",
    trigger_skill_id: "seo_brief", trigger_event: "stage_approved",
    target_team_id: "content-team", target_template_id: "blog_from_brief",
    variable_mapping: { brief: "{{output}}", keywords: "{{keywords}}" },
    auto_start: true, enabled: true, created_at: "2025-01-10T08:00:00Z",
  },
  {
    id: "hnd-demo-2", name: "Blog Approved → Social Posts", source_team_id: "content-team",
    trigger_skill_id: "blog_writer", trigger_event: "workflow_completed",
    target_team_id: "social-team", target_template_id: "social_series",
    variable_mapping: { blog_content: "{{output}}", brand_voice: "{{brand_voice}}" },
    auto_start: true, enabled: true, created_at: "2025-01-12T14:30:00Z",
  },
  {
    id: "hnd-demo-3", name: "Campaign Draft → Email Sequence", source_team_id: "strategy-team",
    trigger_skill_id: null, trigger_event: "stage_approved",
    target_team_id: "email-team", target_template_id: "email_nurture",
    variable_mapping: { campaign_brief: "{{output}}" },
    auto_start: false, enabled: false, created_at: "2025-01-08T11:00:00Z",
  },
];

const STATIC_LOG: LogEntry[] = [
  { id: "hlog-1", rule_id: "hnd-demo-1", source_workflow_id: "wf-101", target_workflow_id: "wf-201", status: "created", error: null, created_at: "2025-01-18T09:15:00Z" },
  { id: "hlog-2", rule_id: "hnd-demo-2", source_workflow_id: "wf-102", target_workflow_id: "wf-202", status: "created", error: null, created_at: "2025-01-17T16:30:00Z" },
  { id: "hlog-3", rule_id: "hnd-demo-1", source_workflow_id: "wf-103", target_workflow_id: null, status: "failed", error: "Template not found", created_at: "2025-01-16T10:00:00Z" },
];

const EVENT_LABELS: Record<string, string> = {
  stage_approved: "Stage Approved",
  workflow_completed: "Workflow Completed",
};

export default function HandoffsPage() {
  const { online, checking } = useBackend();
  const [rules, setRules] = useState<Rule[]>([]);
  const [logEntries, setLogEntries] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"rules" | "log">("rules");
  const [expandedRule, setExpandedRule] = useState<string | null>(null);

  useEffect(() => {
    if (!online) {
      setRules(STATIC_RULES);
      setLogEntries(STATIC_LOG);
      setLoading(false);
      return;
    }
    setLoading(true);
    Promise.all([
      handoffs.list().then((d: any) => setRules(d.rules || [])).catch(() => setRules(STATIC_RULES)),
      handoffs.log().then((d: any) => setLogEntries(d.log || [])).catch(() => setLogEntries(STATIC_LOG)),
    ]).finally(() => setLoading(false));
  }, [online]);

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <GitBranch size={24} /> Cross-Team Handoffs
          </h1>
          <p className="text-gray-500 mt-1 text-sm">
            Automated triggers that pass work between teams when stages are approved.
          </p>
        </div>
        {online && (
          <button className="flex items-center gap-2 bg-brand hover:bg-blue-700 text-white px-4 py-2 rounded-xl text-sm font-medium transition-colors">
            <Plus size={14} /> New Rule
          </button>
        )}
      </div>

      {!online && !checking && (
        <div className="mb-4 flex items-center gap-2 bg-amber-50 border border-amber-200 text-amber-700 px-4 py-2 rounded-lg text-sm">
          <GitBranch size={14} /> Showing demo rules — deploy backend for live data.
        </div>
      )}

      {/* Tabs */}
      <div className="border-b mb-6">
        <div className="flex gap-6">
          <button
            onClick={() => setTab("rules")}
            className={`pb-3 border-b-2 text-sm font-medium transition-colors ${
              tab === "rules" ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            Rules ({rules.length})
          </button>
          <button
            onClick={() => setTab("log")}
            className={`pb-3 border-b-2 text-sm font-medium transition-colors ${
              tab === "log" ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            Execution Log ({logEntries.length})
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-16"><Loader2 size={24} className="animate-spin mx-auto text-gray-400" /></div>
      ) : tab === "rules" ? (
        <div className="space-y-4">
          {rules.length === 0 ? (
            <div className="text-center py-16 text-gray-400">No handoff rules configured.</div>
          ) : (
            rules.map((rule) => (
              <div key={rule.id} className="border rounded-2xl bg-white overflow-hidden">
                <div
                  className="p-5 flex items-center gap-4 cursor-pointer hover:bg-gray-50 transition-colors"
                  onClick={() => setExpandedRule(expandedRule === rule.id ? null : rule.id)}
                >
                  <div className={clsx(
                    "w-3 h-3 rounded-full",
                    rule.enabled ? "bg-green-500" : "bg-gray-300"
                  )} />
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900">{rule.name}</h3>
                    <div className="flex items-center gap-2 mt-1 text-sm text-gray-500">
                      <span className="bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full text-xs">{rule.source_team_id}</span>
                      <ArrowRight size={14} className="text-gray-400" />
                      <span className="bg-purple-50 text-purple-600 px-2 py-0.5 rounded-full text-xs">{rule.target_team_id}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">
                      {EVENT_LABELS[rule.trigger_event] || rule.trigger_event}
                    </span>
                    {rule.auto_start && (
                      <span className="text-xs bg-green-50 text-green-600 px-2 py-0.5 rounded-full flex items-center gap-1">
                        <Zap size={10} /> Auto-start
                      </span>
                    )}
                    {expandedRule === rule.id ? <ChevronUp size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />}
                  </div>
                </div>
                {expandedRule === rule.id && (
                  <div className="border-t px-5 py-4 bg-gray-50 space-y-3">
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <label className="text-xs text-gray-400 uppercase">Trigger Skill</label>
                        <p className="text-gray-700">{rule.trigger_skill_id || "Any skill"}</p>
                      </div>
                      <div>
                        <label className="text-xs text-gray-400 uppercase">Target Template</label>
                        <p className="text-gray-700">{rule.target_template_id}</p>
                      </div>
                    </div>
                    {Object.keys(rule.variable_mapping).length > 0 && (
                      <div>
                        <label className="text-xs text-gray-400 uppercase">Variable Mapping</label>
                        <div className="mt-1 space-y-1">
                          {Object.entries(rule.variable_mapping).map(([k, v]) => (
                            <div key={k} className="flex items-center gap-2 text-sm">
                              <code className="bg-white border px-2 py-0.5 rounded text-xs">{k}</code>
                              <ArrowRight size={12} className="text-gray-400" />
                              <code className="bg-white border px-2 py-0.5 rounded text-xs text-blue-600">{v}</code>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    <div className="flex gap-2 pt-2">
                      <button className="text-xs px-3 py-1.5 border rounded-lg hover:bg-white transition-colors flex items-center gap-1">
                        <Settings2 size={12} /> Edit
                      </button>
                      <button className={clsx(
                        "text-xs px-3 py-1.5 border rounded-lg hover:bg-white transition-colors flex items-center gap-1",
                        rule.enabled ? "text-amber-600" : "text-green-600"
                      )}>
                        {rule.enabled ? <><Pause size={12} /> Disable</> : <><Play size={12} /> Enable</>}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      ) : (
        /* Log Tab */
        <div className="space-y-3">
          {logEntries.length === 0 ? (
            <div className="text-center py-16 text-gray-400">No handoff executions yet.</div>
          ) : (
            logEntries.map((entry) => {
              const rule = rules.find((r) => r.id === entry.rule_id);
              return (
                <div key={entry.id} className="border rounded-xl p-4 bg-white flex items-center gap-4">
                  <div className={clsx(
                    "w-8 h-8 rounded-full flex items-center justify-center",
                    entry.status === "created" ? "bg-green-50 text-green-600" : "bg-red-50 text-red-500"
                  )}>
                    {entry.status === "created" ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">
                      {rule?.name || entry.rule_id}
                    </p>
                    <p className="text-xs text-gray-400">
                      {entry.source_workflow_id}
                      {entry.target_workflow_id && <> → {entry.target_workflow_id}</>}
                    </p>
                    {entry.error && <p className="text-xs text-red-500 mt-1">{entry.error}</p>}
                  </div>
                  <span className="text-xs text-gray-400 flex items-center gap-1">
                    <Clock size={12} /> {new Date(entry.created_at).toLocaleString()}
                  </span>
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
