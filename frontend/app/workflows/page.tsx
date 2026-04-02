"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Plus, Filter, Clock, CheckCircle2, XCircle, AlertTriangle,
  Loader2, ChevronRight, PlayCircle,
} from "lucide-react";
import clsx from "clsx";
import { workflows } from "@/lib/api";
import { useBackend } from "@/lib/useBackend";
import OfflineBanner from "@/components/OfflineBanner";
import DemoBanner from "@/components/DemoBanner";

type Stage = {
  id: string;
  name: string;
  status: string;
  agent_name: string;
  requires_approval: boolean;
};

type Workflow = {
  id: string;
  name: string;
  skill_id: string;
  template_id: string | null;
  status: string;
  current_stage_index: number;
  created_at: string;
  updated_at: string;
  stages: Stage[];
};

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: any }> = {
  active: { label: "Active", color: "text-blue-600 bg-blue-50", icon: PlayCircle },
  completed: { label: "Completed", color: "text-green-600 bg-green-50", icon: CheckCircle2 },
  cancelled: { label: "Cancelled", color: "text-gray-500 bg-gray-50", icon: XCircle },
};

const STAGE_COLORS: Record<string, string> = {
  pending: "bg-gray-200",
  in_progress: "bg-blue-500 animate-pulse",
  awaiting_review: "bg-amber-400",
  approved: "bg-green-500",
  needs_retry: "bg-red-400",
};

export default function WorkflowsPage() {
  const { online, checking } = useBackend();
  const [allWorkflows, setAllWorkflows] = useState<Workflow[]>([]);
  const [filter, setFilter] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [templates, setTemplates] = useState<any[]>([]);

  useEffect(() => {
    if (!online) { setLoading(false); return; }
    loadWorkflows();
    workflows.templates().then(setTemplates).catch(() => {});
  }, [online]);

  const loadWorkflows = () => {
    setLoading(true);
    workflows.list(filter || undefined).then((data) => {
      setAllWorkflows(data);
      setLoading(false);
    }).catch(() => setLoading(false));
  };

  useEffect(() => { if (online) loadWorkflows(); }, [filter, online]);

  const DEMO_WORKFLOWS: Workflow[] = [
    { id: "wf-demo-1", name: "Q3 Blog Series — SEO Optimized", skill_id: "blog_writer", template_id: "seo_blog", status: "active", current_stage_index: 2,
      created_at: "2026-03-25T08:00:00Z", updated_at: "2026-04-01T14:20:00Z",
      stages: [
        { id: "s1", name: "Keyword Research", status: "approved", agent_name: "seo-researcher", requires_approval: false },
        { id: "s2", name: "Outline Draft", status: "approved", agent_name: "content-strategist", requires_approval: true },
        { id: "s3", name: "Full Draft", status: "awaiting_review", agent_name: "blog-writer", requires_approval: true },
        { id: "s4", name: "Brand Voice Check", status: "pending", agent_name: "brand-guardian", requires_approval: false },
      ] },
    { id: "wf-demo-2", name: "Email Nurture — Trial to Paid", skill_id: "email_sequence", template_id: "nurture", status: "active", current_stage_index: 1,
      created_at: "2026-03-28T10:00:00Z", updated_at: "2026-04-01T09:30:00Z",
      stages: [
        { id: "s1", name: "Audience Segmentation", status: "approved", agent_name: "data-analyst", requires_approval: false },
        { id: "s2", name: "Email Copy (5 emails)", status: "in_progress", agent_name: "email-writer", requires_approval: true },
        { id: "s3", name: "Subject Line A/B Test", status: "pending", agent_name: "experiment-agent", requires_approval: true },
      ] },
    { id: "wf-demo-3", name: "Social Launch Posts — Product v2", skill_id: "social_manager", template_id: "launch_social", status: "active", current_stage_index: 0,
      created_at: "2026-04-01T07:00:00Z", updated_at: "2026-04-01T07:00:00Z",
      stages: [
        { id: "s1", name: "Platform Strategy", status: "in_progress", agent_name: "social-strategist", requires_approval: false },
        { id: "s2", name: "Copy Generation", status: "pending", agent_name: "social-writer", requires_approval: true },
        { id: "s3", name: "Visual Brief", status: "pending", agent_name: "design-agent", requires_approval: true },
      ] },
    { id: "wf-demo-4", name: "Competitor SEO Analysis", skill_id: "competitive_intel", template_id: null, status: "completed", current_stage_index: 2,
      created_at: "2026-03-20T09:00:00Z", updated_at: "2026-03-23T16:00:00Z",
      stages: [
        { id: "s1", name: "Data Collection", status: "approved", agent_name: "research-agent", requires_approval: false },
        { id: "s2", name: "Gap Analysis", status: "approved", agent_name: "seo-analyst", requires_approval: true },
        { id: "s3", name: "Report Generation", status: "approved", agent_name: "report-writer", requires_approval: true },
      ] },
    { id: "wf-demo-5", name: "Brand Guidelines Refresh", skill_id: "brand_voice", template_id: null, status: "completed", current_stage_index: 1,
      created_at: "2026-03-15T11:00:00Z", updated_at: "2026-03-18T15:30:00Z",
      stages: [
        { id: "s1", name: "Voice Analysis", status: "approved", agent_name: "brand-analyst", requires_approval: false },
        { id: "s2", name: "Guidelines Draft", status: "approved", agent_name: "brand-writer", requires_approval: true },
      ] },
  ];

  if (!online && !checking) {
    const demoColumns = [
      { key: "active", label: "Active", items: DEMO_WORKFLOWS.filter((w) => w.status === "active") },
      { key: "completed", label: "Completed", items: DEMO_WORKFLOWS.filter((w) => w.status === "completed") },
      { key: "cancelled", label: "Cancelled", items: [] as Workflow[] },
    ];
    return (
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Workflows</h1>
            <p className="text-gray-500 mt-1 text-sm">Track multi-stage marketing workflows end to end.</p>
          </div>
        </div>
        <DemoBanner
          feature="Workflows"
          steps={[
            "Start the backend and navigate to Skills Catalog to pick a workflow template",
            "Fill in variables (brand name, topic, audience) and click \"Start Workflow\"",
            "Approve or reject each stage — agents iterate based on your feedback",
            "Completed workflows feed into Analytics and the learning loop",
          ]}
        />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {demoColumns.map((col) => (
            <div key={col.key}>
              <div className="flex items-center gap-2 mb-3">
                <h3 className="text-sm font-semibold text-gray-600">{col.label}</h3>
                <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">{col.items.length}</span>
              </div>
              <div className="space-y-3">
                {col.items.map((wf) => <WorkflowCard key={wf.id} workflow={wf} />)}
                {col.items.length === 0 && (
                  <div className="text-center py-8 text-xs text-gray-300 border border-dashed rounded-xl">No {col.label.toLowerCase()} workflows</div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!online && !checking) return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-4">Workflows</h1>
      <OfflineBanner><p className="text-sm text-gray-400 max-w-md mx-auto">Multi-stage marketing workflows with agent orchestration and approval gates. Deploy the backend to create and manage workflows.</p></OfflineBanner>
    </div>
  );

  const filtered = allWorkflows;

  // Kanban columns
  const columns = [
    { key: "active", label: "Active", items: filtered.filter((w) => w.status === "active") },
    { key: "completed", label: "Completed", items: filtered.filter((w) => w.status === "completed") },
    { key: "cancelled", label: "Cancelled", items: filtered.filter((w) => w.status === "cancelled") },
  ];

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Workflows</h1>
          <p className="text-gray-500 mt-1 text-sm">Track multi-stage marketing workflows end to end.</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 bg-brand hover:bg-blue-700 text-white px-4 py-2 rounded-xl text-sm font-medium transition-colors"
        >
          <Plus size={14} /> New Workflow
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-2 mb-6">
        {[null, "active", "completed", "cancelled"].map((s) => (
          <button
            key={s || "all"}
            onClick={() => setFilter(s)}
            className={clsx(
              "px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors",
              filter === s ? "bg-gray-900 text-white border-gray-900" : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
            )}
          >
            {s ? s.charAt(0).toUpperCase() + s.slice(1) : "All"} ({s ? columns.find(c => c.key === s)?.items.length || 0 : allWorkflows.length})
          </button>
        ))}
      </div>

      {/* Kanban Board */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="animate-spin text-gray-400" size={24} />
        </div>
      ) : allWorkflows.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <p className="mb-2">No workflows yet.</p>
          <p className="text-sm">Start one from the <Link href="/skills" className="text-brand hover:underline">Skills Catalog</Link> or use a template.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {columns.map((col) => (
            <div key={col.key}>
              <div className="flex items-center gap-2 mb-3">
                <h3 className="text-sm font-semibold text-gray-600">{col.label}</h3>
                <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">{col.items.length}</span>
              </div>
              <div className="space-y-3">
                {col.items.map((wf) => (
                  <WorkflowCard key={wf.id} workflow={wf} />
                ))}
                {col.items.length === 0 && (
                  <div className="text-center py-8 text-xs text-gray-300 border border-dashed rounded-xl">
                    No {col.label.toLowerCase()} workflows
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Modal */}
      {showCreate && (
        <CreateWorkflowModal
          templates={templates}
          onClose={() => setShowCreate(false)}
          onCreated={() => { setShowCreate(false); loadWorkflows(); }}
        />
      )}
    </div>
  );
}

function WorkflowCard({ workflow }: { workflow: Workflow }) {
  const stagesCompleted = workflow.stages.filter((s) => s.status === "approved").length;
  const progress = workflow.stages.length > 0 ? (stagesCompleted / workflow.stages.length) * 100 : 0;
  const currentStage = workflow.stages[workflow.current_stage_index];

  return (
    <Link
      href={`/workflows/${workflow.id}`}
      className="block bg-white border rounded-xl p-4 hover:shadow-md hover:border-brand/30 transition-all group"
    >
      <div className="flex items-start justify-between mb-2">
        <h4 className="font-medium text-sm text-gray-900 line-clamp-1">{workflow.name}</h4>
        <ChevronRight size={14} className="text-gray-300 group-hover:text-brand shrink-0" />
      </div>

      {/* Progress bar */}
      <div className="flex gap-0.5 mb-2">
        {workflow.stages.map((stage) => (
          <div
            key={stage.id}
            className={clsx("h-1.5 rounded-full flex-1", STAGE_COLORS[stage.status] || "bg-gray-200")}
            title={`${stage.name}: ${stage.status}`}
          />
        ))}
      </div>

      <div className="flex items-center justify-between text-[11px] text-gray-500">
        <span>{stagesCompleted}/{workflow.stages.length} stages</span>
        {currentStage && (
          <span className="truncate ml-2">
            {currentStage.status === "awaiting_review" ? (
              <span className="text-amber-600 flex items-center gap-0.5">
                <AlertTriangle size={10} /> Review needed
              </span>
            ) : currentStage.status === "in_progress" ? (
              <span className="text-blue-600 flex items-center gap-0.5">
                <Loader2 size={10} className="animate-spin" /> {currentStage.name}
              </span>
            ) : null}
          </span>
        )}
      </div>

      <div className="text-[10px] text-gray-400 mt-2">
        {workflow.skill_id} &bull; {new Date(workflow.created_at).toLocaleDateString()}
      </div>
    </Link>
  );
}

function CreateWorkflowModal({
  templates,
  onClose,
  onCreated,
}: {
  templates: any[];
  onClose: () => void;
  onCreated: () => void;
}) {
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [variables, setVariables] = useState<Record<string, string>>({});
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  const template = templates.find((t) => t.id === selectedTemplate);

  const create = async () => {
    if (!selectedTemplate) return;
    setCreating(true);
    setError("");
    try {
      await workflows.create({
        template_id: selectedTemplate,
        variables,
        name: name || undefined,
        auto_start: true,
      });
      onCreated();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-2xl w-full max-w-lg mx-4 max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">New Workflow from Template</h2>

          {/* Template picker */}
          <div className="space-y-2 mb-5">
            {templates.map((t) => (
              <button
                key={t.id}
                onClick={() => setSelectedTemplate(t.id)}
                className={clsx(
                  "w-full text-left p-3 rounded-xl border transition-all",
                  selectedTemplate === t.id ? "border-brand bg-blue-50" : "border-gray-200 hover:border-gray-300"
                )}
              >
                <h4 className="font-medium text-sm text-gray-900">{t.name}</h4>
                <p className="text-xs text-gray-500 mt-0.5">{t.description}</p>
                <span className="text-[10px] text-gray-400 mt-1 block">{t.stage_count} stages</span>
              </button>
            ))}
          </div>

          {template && (
            <>
              <input
                type="text"
                placeholder="Workflow name (optional)"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full border rounded-xl px-3 py-2 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-brand"
              />

              {/* Common variables */}
              {["topic", "product_name", "audience", "industry"].map((v) => (
                <div key={v} className="mb-3">
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    {v.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}
                  </label>
                  <input
                    type="text"
                    value={variables[v] || ""}
                    onChange={(e) => setVariables({ ...variables, [v]: e.target.value })}
                    className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand"
                  />
                </div>
              ))}

              {error && <div className="bg-red-50 text-red-700 text-xs px-3 py-2 rounded-lg mb-3">{error}</div>}

              <div className="flex gap-2">
                <button onClick={onClose} className="flex-1 border border-gray-200 text-gray-600 py-2 rounded-xl text-sm hover:bg-gray-50">
                  Cancel
                </button>
                <button
                  onClick={create}
                  disabled={creating}
                  className="flex-1 bg-brand hover:bg-blue-700 text-white py-2 rounded-xl text-sm font-medium disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {creating ? <Loader2 size={14} className="animate-spin" /> : <PlayCircle size={14} />}
                  Start Workflow
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
