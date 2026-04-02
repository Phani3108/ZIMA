"use client";

import { useEffect, useState, useCallback } from "react";
import {
  CheckCircle, XCircle, Circle, ChevronDown, ChevronUp, Save, Trash2,
  ExternalLink, RefreshCw, AlertTriangle, Loader2, Shield, Zap,
  Brain, Palette, Share2, Mail, Search, GitBranch, Users, BarChart,
  Server, Cloud, Wifi, WifiOff, HelpCircle, ChevronRight,
} from "lucide-react";
import clsx from "clsx";

/* ─── Types ─────────────────────────────────────────────────────── */

type KeyDef = { name: string; label: string; secret: boolean };

type Integration = {
  name: string;
  label: string;
  category: string;
  description: string;
  configured: boolean;
  required: boolean;
  key_definitions: KeyDef[];
  setup_url: string;
  setup_steps: string[];
};

type InfraService = {
  label: string;
  category: string;
  description: string;
  env_vars: string[];
  env_status: Record<string, boolean>;
  configured: boolean;
  setup_url: string;
  setup_steps: string[];
};

type TestResult = { ok: boolean; message?: string; error?: string };
type HealthServices = Record<string, { status: string; error?: string; backend?: string }>;

type CategoryMeta = { label: string; icon: string; order: number };

/* ─── Icon helper ───────────────────────────────────────────────── */

const CATEGORY_ICONS: Record<string, React.ComponentType<{ size?: number; className?: string }>> = {
  brain: Brain, palette: Palette, share2: Share2, mail: Mail,
  search: Search, gitBranch: GitBranch, users: Users, barChart: BarChart,
};

/* ─── Status badge ──────────────────────────────────────────────── */

function StatusBadge({ status }: { status: "connected" | "error" | "unconfigured" | "testing" }) {
  if (status === "testing")
    return <span className="flex items-center gap-1 text-xs text-blue-600"><Loader2 size={12} className="animate-spin" />Testing…</span>;
  if (status === "connected")
    return <span className="flex items-center gap-1 text-xs text-green-600"><CheckCircle size={12} />Connected</span>;
  if (status === "error")
    return <span className="flex items-center gap-1 text-xs text-red-600"><XCircle size={12} />Error</span>;
  return <span className="flex items-center gap-1 text-xs text-gray-400"><Circle size={12} />Not configured</span>;
}

/* ─── Reusable test button ──────────────────────────────────────── */

function TestButton({ onClick, loading }: { onClick: () => void; loading: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg border border-blue-200 text-blue-600 hover:bg-blue-50 disabled:opacity-50"
    >
      {loading ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
      {loading ? "Testing…" : "Test Connection"}
    </button>
  );
}

/* ─── Infrastructure card ───────────────────────────────────────── */

function InfraCard({
  id, svc, health, onTest, testResult, testing,
}: {
  id: string;
  svc: InfraService;
  health: { status: string; error?: string } | undefined;
  onTest: () => void;
  testResult: TestResult | null;
  testing: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const isOk = health?.status === "connected" || svc.configured;
  const hasError = health?.status === "error";

  return (
    <div className={clsx(
      "rounded-xl border shadow-sm overflow-hidden",
      hasError ? "border-red-200 bg-red-50/30" : isOk ? "border-green-200 bg-green-50/20" : "border-gray-200 bg-white",
    )}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50/50"
      >
        <div className="flex items-center gap-3">
          {hasError
            ? <XCircle size={18} className="text-red-500" />
            : isOk
              ? <CheckCircle size={18} className="text-green-500" />
              : <AlertTriangle size={18} className="text-amber-400" />
          }
          <div className="text-left">
            <div className="font-medium text-gray-800 text-sm">{svc.label}</div>
            <div className="text-xs text-gray-400">{svc.description}</div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {health?.status === "connected" && <StatusBadge status="connected" />}
          {health?.status === "error" && <StatusBadge status="error" />}
          {!health && !svc.configured && <StatusBadge status="unconfigured" />}
          {!health && svc.configured && <StatusBadge status="connected" />}
          {expanded ? <ChevronUp size={14} className="text-gray-400" /> : <ChevronDown size={14} className="text-gray-400" />}
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-gray-100">
          {/* Env var status */}
          <div className="pt-3">
            <div className="text-xs font-medium text-gray-500 mb-2">Environment Variables</div>
            <div className="space-y-1">
              {svc.env_vars.map((v) => (
                <div key={v} className="flex items-center gap-2 text-xs">
                  {svc.env_status[v]
                    ? <CheckCircle size={12} className="text-green-500" />
                    : <XCircle size={12} className="text-red-400" />
                  }
                  <code className="text-gray-600 bg-gray-100 px-1.5 py-0.5 rounded">{v}</code>
                  <span className={svc.env_status[v] ? "text-green-600" : "text-red-500"}>
                    {svc.env_status[v] ? "Set" : "Missing"}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Setup steps */}
          {svc.setup_steps.length > 0 && (
            <div>
              <div className="text-xs font-medium text-gray-500 mb-2">Setup Steps</div>
              <ol className="space-y-1 text-xs text-gray-600 list-decimal list-inside">
                {svc.setup_steps.map((step, i) => <li key={i}>{step}</li>)}
              </ol>
            </div>
          )}

          {/* Error display */}
          {health?.error && (
            <div className="bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              <div className="text-xs font-medium text-red-700 mb-1">Error Details</div>
              <p className="text-xs text-red-600 font-mono break-all">{health.error}</p>
            </div>
          )}

          {/* Test result */}
          {testResult && (
            <div className={clsx(
              "rounded-lg px-3 py-2 border",
              testResult.ok ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200",
            )}>
              <p className={clsx("text-xs", testResult.ok ? "text-green-700" : "text-red-600")}>
                {testResult.ok ? testResult.message : testResult.error}
              </p>
            </div>
          )}

          <div className="flex gap-2 pt-1">
            <TestButton onClick={onTest} loading={testing} />
            {svc.setup_url && (
              <a
                href={svc.setup_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
              >
                <ExternalLink size={12} /> Open Portal
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* ─── Integration card ──────────────────────────────────────────── */

function IntegrationCard({
  intg, onSave, onRemove, onTest, testResult, testing, saving, forms, setForms,
}: {
  intg: Integration;
  onSave: () => void;
  onRemove: () => void;
  onTest: () => void;
  testResult: TestResult | null;
  testing: boolean;
  saving: boolean;
  forms: Record<string, string>;
  setForms: (name: string, key: string, value: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [showSteps, setShowSteps] = useState(false);

  return (
    <div className={clsx(
      "rounded-xl border shadow-sm overflow-hidden",
      intg.configured ? "border-green-100 bg-white" : "border-gray-200 bg-white",
    )}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50"
      >
        <div className="flex items-center gap-3">
          {intg.configured
            ? <CheckCircle size={18} className="text-green-500" />
            : <Circle size={18} className="text-gray-300" />
          }
          <div className="text-left">
            <div className="font-medium text-gray-800 text-sm">{intg.label}</div>
            <div className="text-xs text-gray-400">{intg.description}</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={intg.configured ? "connected" : "unconfigured"} />
          {expanded ? <ChevronUp size={14} className="text-gray-400" /> : <ChevronDown size={14} className="text-gray-400" />}
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-gray-100">
          {/* Setup guide toggle */}
          {intg.setup_steps.length > 0 && (
            <div className="pt-3">
              <button
                onClick={() => setShowSteps(!showSteps)}
                className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700"
              >
                <HelpCircle size={12} />
                {showSteps ? "Hide setup guide" : "How to get credentials"}
                <ChevronRight size={12} className={clsx("transition-transform", showSteps && "rotate-90")} />
              </button>
              {showSteps && (
                <div className="mt-2 bg-blue-50 border border-blue-100 rounded-lg px-3 py-2">
                  <ol className="space-y-1 text-xs text-blue-800 list-decimal list-inside">
                    {intg.setup_steps.map((step, i) => <li key={i}>{step}</li>)}
                  </ol>
                  {intg.setup_url && (
                    <a
                      href={intg.setup_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 mt-2 text-xs text-blue-700 font-medium hover:underline"
                    >
                      <ExternalLink size={11} /> Open {intg.label} setup page →
                    </a>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Key inputs */}
          <div className="space-y-2 pt-1">
            {intg.key_definitions.map((kd) => (
              <div key={kd.name}>
                <label className="block text-xs font-medium text-gray-600 mb-1">{kd.label}</label>
                <input
                  type={kd.secret ? "password" : "text"}
                  placeholder={intg.configured ? "••••••••  (already saved)" : kd.label}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent"
                  value={forms[kd.name] || ""}
                  onChange={(e) => setForms(intg.name, kd.name, e.target.value)}
                />
              </div>
            ))}
          </div>

          {/* Test result */}
          {testResult && (
            <div className={clsx(
              "rounded-lg px-3 py-2 border",
              testResult.ok ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200",
            )}>
              <p className={clsx("text-xs font-medium mb-0.5", testResult.ok ? "text-green-700" : "text-red-700")}>
                {testResult.ok ? "✓ Connection successful" : "✗ Connection failed"}
              </p>
              <p className={clsx("text-xs", testResult.ok ? "text-green-600" : "text-red-600")}>
                {testResult.ok ? testResult.message : testResult.error}
              </p>
            </div>
          )}

          {/* Actions */}
          <div className="flex flex-wrap gap-2 pt-1">
            <button
              onClick={onSave}
              disabled={saving}
              className="flex items-center gap-1 bg-blue-600 hover:bg-blue-700 text-white text-xs px-4 py-2 rounded-lg disabled:opacity-50 transition-colors"
            >
              {saving ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
              {saving ? "Saving…" : "Save Credentials"}
            </button>
            {intg.configured && (
              <TestButton onClick={onTest} loading={testing} />
            )}
            {intg.configured && (
              <button
                onClick={onRemove}
                className="flex items-center gap-1 text-red-600 hover:text-red-700 text-xs px-3 py-2 rounded-lg border border-red-200 hover:bg-red-50 transition-colors"
              >
                <Trash2 size={12} /> Remove
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* ─── Overview banner ───────────────────────────────────────────── */

function OverviewBanner({ infraCount, infraOk, intgCount, intgOk }: {
  infraCount: number; infraOk: number; intgCount: number; intgOk: number;
}) {
  const allGood = infraOk === infraCount && intgOk > 0;
  return (
    <div className={clsx(
      "rounded-xl border px-5 py-4 mb-6",
      allGood ? "bg-green-50 border-green-200" : "bg-amber-50 border-amber-200",
    )}>
      <div className="flex items-start gap-3">
        {allGood
          ? <Shield size={24} className="text-green-600 mt-0.5" />
          : <AlertTriangle size={24} className="text-amber-600 mt-0.5" />
        }
        <div>
          <h2 className="font-semibold text-gray-800 text-sm">
            {allGood ? "System Ready" : "Setup Required"}
          </h2>
          <p className="text-xs text-gray-600 mt-1">
            Infrastructure: <strong>{infraOk}/{infraCount}</strong> services connected
            &nbsp;·&nbsp;
            Integrations: <strong>{intgOk}/{intgCount}</strong> configured
          </p>
          {!allGood && (
            <p className="text-xs text-amber-700 mt-1">
              Scroll down to configure missing services. Each card has step-by-step instructions and a test button.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─── Main page ─────────────────────────────────────────────────── */

export default function SettingsPage() {
  // State
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [infra, setInfra] = useState<Record<string, InfraService>>({});
  const [categories, setCategories] = useState<Record<string, CategoryMeta>>({});
  const [health, setHealth] = useState<HealthServices>({});
  const [forms, setForms] = useState<Record<string, Record<string, string>>>({});
  const [saving, setSaving] = useState<string | null>(null);
  const [testing, setTesting] = useState<Record<string, boolean>>({});
  const [testResults, setTestResults] = useState<Record<string, TestResult>>({});
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"overview" | "infra" | "integrations">("overview");

  // Fetch everything on mount
  useEffect(() => {
    Promise.all([
      fetch("/api/settings/integrations").then((r) => r.json()),
      fetch("/api/health/system").then((r) => r.json()),
      fetch("/api/health").then((r) => r.json()),
    ])
      .then(([intgData, sysData, healthData]) => {
        setIntegrations(intgData);
        setInfra(sysData.infra || {});
        setCategories(sysData.categories || {});
        setHealth(healthData.services || {});
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load settings:", err);
        setLoading(false);
      });
  }, []);

  const setField = (integration: string, key: string, value: string) => {
    setForms((f) => ({ ...f, [integration]: { ...(f[integration] || {}), [key]: value } }));
  };

  const save = async (name: string) => {
    const keys = forms[name] || {};
    const hasValues = Object.values(keys).some((v) => v.trim());
    if (!hasValues) return;

    setSaving(name);
    try {
      const r = await fetch(`/api/settings/integrations/${name}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ keys }),
      });
      const data = await r.json();
      if (data.ok) {
        setIntegrations((prev) => prev.map((i) => i.name === name ? { ...i, configured: true } : i));
        setTestResults((prev) => ({ ...prev, [name]: { ok: true, message: "Credentials saved successfully." } }));
        // Auto-test after save
        testIntegration(name);
      } else {
        setTestResults((prev) => ({ ...prev, [name]: { ok: false, error: data.detail || "Failed to save." } }));
      }
    } catch (e: any) {
      setTestResults((prev) => ({ ...prev, [name]: { ok: false, error: e.message } }));
    }
    setSaving(null);
  };

  const remove = async (name: string) => {
    if (!confirm(`Remove all credentials for ${integrations.find((i) => i.name === name)?.label || name}?`)) return;
    await fetch(`/api/settings/integrations/${name}`, { method: "DELETE" });
    setIntegrations((prev) => prev.map((i) => i.name === name ? { ...i, configured: false } : i));
    setTestResults((prev) => {
      const copy = { ...prev };
      delete copy[name];
      return copy;
    });
  };

  const testIntegration = async (name: string) => {
    setTesting((t) => ({ ...t, [name]: true }));
    try {
      const r = await fetch(`/api/settings/integrations/${name}/test`, { method: "POST" });
      const data = await r.json();
      setTestResults((prev) => ({ ...prev, [name]: data }));
    } catch (e: any) {
      setTestResults((prev) => ({ ...prev, [name]: { ok: false, error: e.message } }));
    }
    setTesting((t) => ({ ...t, [name]: false }));
  };

  const testInfra = async (service: string) => {
    setTesting((t) => ({ ...t, [`infra_${service}`]: true }));
    try {
      const r = await fetch(`/api/settings/infra/test/${service}`, { method: "POST" });
      const data = await r.json();
      setTestResults((prev) => ({ ...prev, [`infra_${service}`]: data }));
    } catch (e: any) {
      setTestResults((prev) => ({ ...prev, [`infra_${service}`]: { ok: false, error: e.message } }));
    }
    setTesting((t) => ({ ...t, [`infra_${service}`]: false }));
  };

  // Test all integrations
  const testAll = async () => {
    // Test infra
    for (const svc of Object.keys(infra)) {
      testInfra(svc);
    }
    // Test configured integrations
    for (const intg of integrations.filter((i) => i.configured)) {
      testIntegration(intg.name);
    }
  };

  // Counts
  const infraEntries = Object.entries(infra);
  const infraCount = infraEntries.filter(([k]) => ["postgresql", "redis", "qdrant"].includes(k)).length;
  const infraOk = infraEntries.filter(([k, v]) => ["postgresql", "redis", "qdrant"].includes(k) && v.configured).length;
  const intgCount = integrations.length;
  const intgOk = integrations.filter((i) => i.configured).length;

  // Group integrations by category
  const grouped = integrations.reduce<Record<string, Integration[]>>((acc, intg) => {
    const cat = intg.category || "other";
    (acc[cat] = acc[cat] || []).push(intg);
    return acc;
  }, {});

  // Sort categories by order
  const sortedCategories = Object.entries(grouped).sort(([a], [b]) => {
    return (categories[a]?.order ?? 99) - (categories[b]?.order ?? 99);
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 size={32} className="animate-spin text-blue-500" />
        <span className="ml-3 text-gray-500">Loading system status…</span>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div>
          <h1 className="text-xl font-semibold text-gray-800 flex items-center gap-2">
            <Zap size={20} className="text-blue-600" />
            Setup & Integrations
          </h1>
          <p className="text-xs text-gray-400 mt-1">
            Configure all services from here. Credentials are encrypted with Fernet + Azure Key Vault.
          </p>
        </div>
        <button
          onClick={testAll}
          className="flex items-center gap-1 text-xs px-3 py-2 rounded-lg bg-gray-800 text-white hover:bg-gray-900 transition-colors"
        >
          <RefreshCw size={12} /> Test All
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200 mb-6 mt-4">
        {(
          [
            { id: "overview", label: "Overview", icon: Shield },
            { id: "infra", label: "Infrastructure", icon: Server },
            { id: "integrations", label: "Integrations", icon: Zap },
          ] as const
        ).map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={clsx(
              "flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px",
              tab === id
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            )}
          >
            <Icon size={14} /> {label}
          </button>
        ))}
      </div>

      {/* ─── Overview tab ──────────────────────────────────────── */}
      {tab === "overview" && (
        <div>
          <OverviewBanner infraCount={infraCount} infraOk={infraOk} intgCount={intgCount} intgOk={intgOk} />

          {/* Infra summary */}
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <Server size={14} /> Infrastructure Services
          </h3>
          <div className="grid grid-cols-2 gap-3 mb-6">
            {infraEntries.map(([id, svc]) => {
              const h = health[id];
              const isOk = h?.status === "connected" || svc.configured;
              const isError = h?.status === "error";
              return (
                <div
                  key={id}
                  className={clsx(
                    "rounded-lg border px-3 py-2.5 cursor-pointer hover:shadow-sm transition-shadow",
                    isError ? "border-red-200 bg-red-50/40" : isOk ? "border-green-200 bg-green-50/30" : "border-amber-200 bg-amber-50/30",
                  )}
                  onClick={() => setTab("infra")}
                >
                  <div className="flex items-center gap-2">
                    {isError ? <XCircle size={14} className="text-red-500" />
                      : isOk ? <CheckCircle size={14} className="text-green-500" />
                      : <AlertTriangle size={14} className="text-amber-500" />}
                    <span className="text-sm font-medium text-gray-700">{svc.label}</span>
                  </div>
                  {isError && h?.error && (
                    <p className="text-xs text-red-500 mt-1 truncate">{h.error}</p>
                  )}
                </div>
              );
            })}
          </div>

          {/* Integration summary by category */}
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <Zap size={14} /> Integration Status
          </h3>
          <div className="space-y-2">
            {sortedCategories.map(([catKey, items]) => {
              const catMeta = categories[catKey];
              const configuredCount = items.filter((i) => i.configured).length;
              return (
                <div
                  key={catKey}
                  className="flex items-center justify-between rounded-lg border border-gray-200 px-4 py-2.5 cursor-pointer hover:bg-gray-50 transition-colors"
                  onClick={() => setTab("integrations")}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-700">{catMeta?.label || catKey}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-gray-400">
                      {configuredCount}/{items.length} configured
                    </span>
                    <div className="flex gap-0.5">
                      {items.map((i) => (
                        <div
                          key={i.name}
                          className={clsx(
                            "w-2 h-2 rounded-full",
                            i.configured ? "bg-green-400" : "bg-gray-300",
                          )}
                          title={`${i.label}: ${i.configured ? "configured" : "not configured"}`}
                        />
                      ))}
                    </div>
                    <ChevronRight size={14} className="text-gray-400" />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ─── Infrastructure tab ────────────────────────────────── */}
      {tab === "infra" && (
        <div className="space-y-3">
          <p className="text-xs text-gray-500 mb-4">
            Infrastructure services are configured via environment variables. Each card shows which variables are set or missing, with instructions to configure them.
          </p>

          {/* Core infra */}
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Core Services</h3>
          {infraEntries
            .filter(([, s]) => s.category === "infrastructure")
            .map(([id, svc]) => (
              <InfraCard
                key={id}
                id={id}
                svc={svc}
                health={health[id]}
                onTest={() => testInfra(id)}
                testResult={testResults[`infra_${id}`] || null}
                testing={testing[`infra_${id}`] || false}
              />
            ))}

          {/* Microsoft */}
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 mt-6">Microsoft & Teams</h3>
          {infraEntries
            .filter(([, s]) => s.category === "microsoft")
            .map(([id, svc]) => (
              <InfraCard
                key={id}
                id={id}
                svc={svc}
                health={health[id]}
                onTest={() => testInfra(id)}
                testResult={testResults[`infra_${id}`] || null}
                testing={testing[`infra_${id}`] || false}
              />
            ))}

          {/* Azure */}
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 mt-6">Azure Cloud Services</h3>
          {infraEntries
            .filter(([, s]) => s.category === "azure")
            .map(([id, svc]) => (
              <InfraCard
                key={id}
                id={id}
                svc={svc}
                health={health[id]}
                onTest={() => testInfra(id)}
                testResult={testResults[`infra_${id}`] || null}
                testing={testing[`infra_${id}`] || false}
              />
            ))}
        </div>
      )}

      {/* ─── Integrations tab ──────────────────────────────────── */}
      {tab === "integrations" && (
        <div className="space-y-6">
          <p className="text-xs text-gray-500 mb-4">
            API keys are encrypted and stored in the vault. After saving, click "Test Connection" to verify. Each card has a setup guide with links to get your credentials.
          </p>

          {sortedCategories.map(([catKey, items]) => {
            const catMeta = categories[catKey];
            return (
              <div key={catKey}>
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                  {catMeta?.label || catKey}
                </h3>
                <div className="space-y-2">
                  {items.map((intg) => (
                    <IntegrationCard
                      key={intg.name}
                      intg={intg}
                      onSave={() => save(intg.name)}
                      onRemove={() => remove(intg.name)}
                      onTest={() => testIntegration(intg.name)}
                      testResult={testResults[intg.name] || null}
                      testing={testing[intg.name] || false}
                      saving={saving === intg.name}
                      forms={forms[intg.name] || {}}
                      setForms={setField}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Footer */}
      <div className="mt-8 border-t border-gray-200 pt-4">
        <p className="text-[10px] text-gray-300 text-center">
          Zeta IMA v0.7.0 · All credentials encrypted with AES-128-CBC · Never stored in plaintext
        </p>
      </div>
    </div>
  );
}
