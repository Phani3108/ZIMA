"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  BarChart3, Activity, AlertTriangle, Cpu, TrendingUp,
  ArrowUpRight, Loader2, RefreshCw, CheckCircle2, XCircle, Clock, WifiOff,
} from "lucide-react";
import clsx from "clsx";
import { dashboard } from "@/lib/api";
import DemoBanner from "@/components/DemoBanner";

type Summary = {
  workflows: { total: number; active: number; completed: number; cancelled: number };
  stages: { total: number; completed: number; failed: number; awaiting_review: number; stuck: number };
  completion_rate: number;
  stage_success_rate: number;
};

type ActivityEvent = {
  workflow_id: string;
  workflow_name: string;
  stage_id: string;
  stage_name: string;
  stage_status: string;
  agent: string;
  llm_used: string | null;
  error: string | null;
  timestamp: string;
};

type StuckItem = {
  workflow_id: string;
  workflow_name: string;
  stage_id: string;
  stage_name: string;
  stage_status: string;
  agent: string;
  reason: string;
  owner: string | null;
  started_at: string | null;
};

type AgentInfo = {
  providers: Record<string, boolean>;
  llm_usage: Record<string, number>;
  agent_usage: Record<string, number>;
  agents: { name: string; description: string; status: string }[];
};

export default function DashboardPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [activity, setActivity] = useState<ActivityEvent[]>([]);
  const [stuck, setStuck] = useState<StuckItem[]>([]);
  const [agents, setAgents] = useState<AgentInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"overview" | "activity" | "stuck" | "agents">("overview");
  const [backendOnline, setBackendOnline] = useState(true);

  const loadAll = () => {
    setLoading(true);
    Promise.all([
      dashboard.summary().catch(() => null),
      dashboard.activity(20).catch(() => []),
      dashboard.stuck().catch(() => []),
      dashboard.agents().catch(() => null),
    ]).then(([s, a, st, ag]) => {
      if (!s && (!a || a.length === 0) && (!st || st.length === 0) && !ag) {
        setBackendOnline(false);
      }
      if (s) setSummary(s);
      setActivity(a || []);
      setStuck(st || []);
      if (ag) setAgents(ag);
      setLoading(false);
    });
  };

  useEffect(() => { loadAll(); }, []);

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Program Dashboard</h1>
          <p className="text-gray-500 mt-1 text-sm">
            Real-time overview of all marketing workflows, agent health, and escalations.
          </p>
        </div>
        <button
          onClick={loadAll}
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-brand"
        >
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="animate-spin text-gray-400" size={24} />
        </div>
      ) : !backendOnline ? (
        <>
          <DemoBanner
            feature="Dashboard"
            steps={[
              "Run docker compose up to start Redis, PostgreSQL, and Qdrant",
              "Start the backend with uvicorn zeta_ima.api.app:app --reload",
              "Create workflows from the Skills Catalog or Chat — metrics appear automatically",
            ]}
          />
          {/* Demo KPI cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-8">
            <KPICard label="Total Workflows" value={24} icon={BarChart3} />
            <KPICard label="Active" value={5} icon={Activity} color="text-blue-600" />
            <KPICard label="Completed" value={17} icon={CheckCircle2} color="text-green-600" />
            <KPICard label="Completion Rate" value="87%" icon={TrendingUp} color="text-brand" />
            <KPICard label="Awaiting Review" value={3} icon={Clock} color="text-amber-600" />
            <KPICard label="Stuck Stages" value={1} icon={AlertTriangle} color="text-red-600" />
          </div>
          {/* Demo Activity Feed */}
          <h3 className="text-sm font-semibold text-gray-600 mb-3">Recent Activity</h3>
          <div className="space-y-2 mb-6">
            {[
              { name: "Q3 Blog Series", stage: "SEO Review", status: "awaiting_review", agent: "seo-reviewer", time: "2 min ago" },
              { name: "Email Nurture Campaign", stage: "Copy Generation", status: "approved", agent: "email-writer", time: "8 min ago" },
              { name: "Social Launch Posts", stage: "Brand Voice Check", status: "in_progress", agent: "brand-guardian", time: "15 min ago" },
              { name: "Competitor Analysis", stage: "Data Collection", status: "approved", agent: "research-agent", time: "1 hr ago" },
              { name: "Product Landing Page", stage: "CTA Optimization", status: "needs_retry", agent: "conversion-agent", time: "2 hr ago" },
            ].map((e, i) => {
              const icons: Record<string, any> = { approved: CheckCircle2, needs_retry: XCircle, awaiting_review: Clock, in_progress: Loader2 };
              const colors: Record<string, string> = { approved: "text-green-600", needs_retry: "text-red-600", awaiting_review: "text-amber-600", in_progress: "text-blue-600" };
              const Icon = icons[e.status] || Clock;
              return (
                <div key={i} className="flex items-center gap-3 bg-white border rounded-lg px-4 py-3">
                  <Icon size={14} className={clsx(colors[e.status] || "text-gray-400", e.status === "in_progress" && "animate-spin")} />
                  <div className="flex-1 min-w-0">
                    <span className="text-sm text-gray-800 font-medium">{e.name}</span>
                    <span className="text-gray-400 mx-2">→</span>
                    <span className="text-sm text-gray-500">{e.stage}</span>
                  </div>
                  <span className="text-xs text-gray-400 shrink-0">{e.agent}</span>
                  <span className="text-[11px] text-gray-400 shrink-0 w-16 text-right">{e.time}</span>
                </div>
              );
            })}
          </div>
          {/* Stuck demo */}
          <h3 className="text-sm font-semibold text-gray-600 mb-3">Escalations</h3>
          <div className="bg-white border border-amber-200 rounded-xl p-4">
            <div className="flex items-center gap-3">
              <AlertTriangle size={16} className="text-amber-500" />
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">Product Landing Page — CTA Optimization</p>
                <p className="text-xs text-gray-500">Stuck for 4 hours · Agent: conversion-agent · Reason: Low conversion score (3/10)</p>
              </div>
              <span className="text-xs bg-amber-100 text-amber-700 px-2 py-1 rounded-full">Needs attention</span>
            </div>
          </div>
        </>
      ) : (
        <>
          {/* KPI Cards */}
          {summary && (
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-8">
              <KPICard label="Total Workflows" value={summary.workflows.total} icon={BarChart3} />
              <KPICard label="Active" value={summary.workflows.active} icon={Activity} color="text-blue-600" />
              <KPICard label="Completed" value={summary.workflows.completed} icon={CheckCircle2} color="text-green-600" />
              <KPICard label="Completion Rate" value={`${summary.completion_rate}%`} icon={TrendingUp} color="text-brand" />
              <KPICard label="Awaiting Review" value={summary.stages.awaiting_review} icon={Clock} color="text-amber-600" />
              <KPICard
                label="Stuck Stages"
                value={summary.stages.stuck}
                icon={AlertTriangle}
                color={summary.stages.stuck > 0 ? "text-red-600" : "text-green-600"}
              />
            </div>
          )}

          {/* Tabs */}
          <div className="flex gap-1 mb-6 border-b">
            {[
              { key: "overview", label: "Activity Feed", icon: Activity },
              { key: "stuck", label: `Escalations (${stuck.length})`, icon: AlertTriangle },
              { key: "agents", label: "Agents & LLMs", icon: Cpu },
            ].map((t) => (
              <button
                key={t.key}
                onClick={() => setTab(t.key as any)}
                className={clsx(
                  "flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-[1px]",
                  tab === t.key
                    ? "border-brand text-brand"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                )}
              >
                <t.icon size={14} />
                {t.label}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          {tab === "overview" && <ActivityFeed events={activity} />}
          {tab === "stuck" && <StuckList items={stuck} />}
          {tab === "agents" && agents && <AgentsPanel data={agents} />}
        </>
      )}
    </div>
  );
}

function KPICard({
  label,
  value,
  icon: Icon,
  color = "text-gray-900",
}: {
  label: string;
  value: string | number;
  icon: any;
  color?: string;
}) {
  return (
    <div className="bg-white border rounded-xl p-4">
      <div className="flex items-center gap-2 mb-2">
        <Icon size={14} className="text-gray-400" />
        <span className="text-[11px] text-gray-500 uppercase tracking-wider">{label}</span>
      </div>
      <div className={clsx("text-2xl font-bold", color)}>{value}</div>
    </div>
  );
}

function ActivityFeed({ events }: { events: ActivityEvent[] }) {
  const statusIcon: Record<string, any> = {
    approved: CheckCircle2,
    needs_retry: XCircle,
    awaiting_review: Clock,
    in_progress: Loader2,
  };

  const statusColor: Record<string, string> = {
    approved: "text-green-600",
    needs_retry: "text-red-600",
    awaiting_review: "text-amber-600",
    in_progress: "text-blue-600",
  };

  if (events.length === 0) {
    return <div className="text-center py-12 text-gray-400">No activity yet</div>;
  }

  return (
    <div className="space-y-2">
      {events.map((event, i) => {
        const Icon = statusIcon[event.stage_status] || Clock;
        return (
          <Link
            key={i}
            href={`/workflows/${event.workflow_id}`}
            className="flex items-center gap-3 bg-white border rounded-lg px-4 py-3 hover:shadow-sm transition-shadow group"
          >
            <Icon
              size={14}
              className={clsx(statusColor[event.stage_status] || "text-gray-400",
                event.stage_status === "in_progress" && "animate-spin")}
            />
            <div className="flex-1 min-w-0">
              <span className="text-sm text-gray-900 font-medium">{event.stage_name}</span>
              <span className="text-xs text-gray-400 ml-2">{event.workflow_name}</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-400">
              {event.llm_used && <span className="bg-gray-100 px-1.5 py-0.5 rounded">{event.llm_used}</span>}
              <span>{event.agent}</span>
              <span>{event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : ""}</span>
              <ArrowUpRight size={12} className="text-gray-300 group-hover:text-brand" />
            </div>
          </Link>
        );
      })}
    </div>
  );
}

function StuckList({ items }: { items: StuckItem[] }) {
  if (items.length === 0) {
    return (
      <div className="text-center py-12 text-green-600">
        <CheckCircle2 size={24} className="mx-auto mb-2" />
        <p>All clear! No stuck stages.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {items.map((item, i) => (
        <Link
          key={i}
          href={`/workflows/${item.workflow_id}`}
          className="block bg-white border border-red-100 rounded-xl p-4 hover:shadow-sm transition-shadow"
        >
          <div className="flex items-start justify-between">
            <div>
              <h4 className="font-medium text-sm text-gray-900">
                <AlertTriangle size={12} className="inline text-red-500 mr-1" />
                {item.stage_name}
              </h4>
              <p className="text-xs text-gray-500 mt-0.5">{item.workflow_name}</p>
            </div>
            <span className={clsx(
              "text-xs px-2 py-0.5 rounded-full",
              item.stage_status === "needs_retry" ? "bg-red-100 text-red-600" : "bg-amber-100 text-amber-600"
            )}>
              {item.stage_status.replace("_", " ")}
            </span>
          </div>
          <p className="text-xs text-red-600 mt-2">{item.reason}</p>
          <div className="flex items-center gap-3 mt-2 text-[11px] text-gray-400">
            <span>Agent: {item.agent}</span>
            {item.owner && <span>Owner: {item.owner}</span>}
            {item.started_at && <span>Since: {new Date(item.started_at).toLocaleString()}</span>}
          </div>
        </Link>
      ))}
    </div>
  );
}

function AgentsPanel({ data }: { data: AgentInfo }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* LLM Providers */}
      <div className="bg-white border rounded-xl p-5">
        <h3 className="font-semibold text-sm text-gray-900 mb-4">LLM Provider Status</h3>
        <div className="space-y-2">
          {Object.entries(data.providers).map(([provider, available]) => (
            <div key={provider} className="flex items-center justify-between py-2 border-b last:border-0">
              <span className="text-sm text-gray-700">{provider}</span>
              <span className={clsx(
                "flex items-center gap-1 text-xs font-medium",
                available ? "text-green-600" : "text-red-500"
              )}>
                {available ? <><CheckCircle2 size={12} /> Connected</> : <><XCircle size={12} /> Not Configured</>}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Agent Status */}
      <div className="bg-white border rounded-xl p-5">
        <h3 className="font-semibold text-sm text-gray-900 mb-4">Agents</h3>
        <div className="space-y-2">
          {data.agents.map((agent) => (
            <div key={agent.name} className="flex items-center justify-between py-2 border-b last:border-0">
              <div>
                <span className="text-sm text-gray-700 font-medium">{agent.name}</span>
                <p className="text-[11px] text-gray-400">{agent.description}</p>
              </div>
              <span className="text-xs bg-green-100 text-green-600 px-2 py-0.5 rounded-full">{agent.status}</span>
            </div>
          ))}
        </div>
      </div>

      {/* LLM Usage */}
      {Object.keys(data.llm_usage).length > 0 && (
        <div className="bg-white border rounded-xl p-5">
          <h3 className="font-semibold text-sm text-gray-900 mb-4">LLM Usage (Recent)</h3>
          <div className="space-y-2">
            {Object.entries(data.llm_usage).map(([llm, count]) => (
              <div key={llm} className="flex items-center justify-between py-1">
                <span className="text-sm text-gray-700">{llm}</span>
                <span className="text-sm font-semibold text-brand">{count} calls</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Agent Usage */}
      {Object.keys(data.agent_usage).length > 0 && (
        <div className="bg-white border rounded-xl p-5">
          <h3 className="font-semibold text-sm text-gray-900 mb-4">Agent Usage (Recent)</h3>
          <div className="space-y-2">
            {Object.entries(data.agent_usage).map(([agent, count]) => (
              <div key={agent} className="flex items-center justify-between py-1">
                <span className="text-sm text-gray-700">{agent}</span>
                <span className="text-sm font-semibold text-gray-600">{count} tasks</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
