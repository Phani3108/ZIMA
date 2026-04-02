"use client";

import { useState, useEffect, useCallback } from "react";
import { DollarSign, RefreshCw, Loader2, TrendingUp, AlertTriangle } from "lucide-react";
import clsx from "clsx";
import { costs } from "@/lib/api";
import { useBackend } from "@/lib/useBackend";
import OfflineBanner from "@/components/OfflineBanner";

type Report = {
  total_cost: number;
  total_tokens: number;
  total_requests: number;
  by_model: Record<string, { cost: number; tokens: number; requests: number }>;
  period_days: number;
};

type DailyEntry = {
  date: string;
  cost: number;
  tokens: number;
  requests: number;
};

type Limits = {
  requests_remaining: number;
  tokens_remaining: number;
  daily_limit: number;
  usage_pct: number;
};

export default function CostsPage() {
  const { online, checking } = useBackend();
  const [report, setReport] = useState<Report | null>(null);
  const [daily, setDaily] = useState<DailyEntry[]>([]);
  const [limits, setLimits] = useState<Limits | null>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);

  const load = useCallback(() => {
    if (!online) { setLoading(false); return; }
    setLoading(true);
    Promise.all([costs.report(days), costs.daily(days), costs.limits()])
      .then(([r, d, l]) => { setReport(r); setDaily(d); setLimits(l); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [days, online]);

  useEffect(() => { load(); }, [load]);

  if (!online && !checking) return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2 mb-4"><DollarSign size={22} /> Cost Tracker</h1>
      <OfflineBanner><p className="text-sm text-gray-400 max-w-md mx-auto">Tracks LLM spending, token usage, and rate limits across all agents. Deploy the backend to see cost data.</p></OfflineBanner>
    </div>
  );

  const maxCost = Math.max(...daily.map(d => d.cost), 0.01);

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <DollarSign size={22} /> Cost Tracker
          </h1>
          <p className="text-gray-500 text-sm mt-1">LLM spending, token usage, and rate limits.</p>
        </div>
        <div className="flex gap-2 items-center">
          <select value={days} onChange={(e) => setDays(Number(e.target.value))}
            className="border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand">
            <option value={7}>7 days</option>
            <option value={14}>14 days</option>
            <option value={30}>30 days</option>
            <option value={90}>90 days</option>
          </select>
          <button onClick={load} className="p-2 rounded-lg border hover:bg-gray-50"><RefreshCw size={16} /></button>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-20"><Loader2 className="animate-spin text-gray-400" size={24} /></div>
      ) : (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-8">
            <SummaryCard label="Total Cost" value={`$${(report?.total_cost ?? 0).toFixed(2)}`} icon={DollarSign} />
            <SummaryCard label="Total Tokens" value={formatNumber(report?.total_tokens ?? 0)} icon={TrendingUp} />
            <SummaryCard label="Requests" value={formatNumber(report?.total_requests ?? 0)} icon={TrendingUp} />
            {limits && (
              <div className={clsx("bg-white border rounded-xl p-4", limits.usage_pct > 80 && "border-red-300")}>
                <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
                  {limits.usage_pct > 80 && <AlertTriangle size={12} className="text-red-500" />}
                  Usage
                </div>
                <div className="text-xl font-bold text-gray-900">{limits.usage_pct.toFixed(0)}%</div>
                <div className="w-full bg-gray-100 rounded-full h-1.5 mt-2">
                  <div className={clsx("h-1.5 rounded-full", limits.usage_pct > 80 ? "bg-red-500" : "bg-brand")}
                    style={{ width: `${Math.min(limits.usage_pct, 100)}%` }} />
                </div>
              </div>
            )}
          </div>

          {/* Daily chart */}
          <div className="bg-white border rounded-xl p-6 mb-8">
            <h3 className="font-semibold text-sm text-gray-900 mb-4">Daily Spend</h3>
            {daily.length === 0 ? (
              <div className="text-center py-10 text-gray-400 text-sm">No data for this period.</div>
            ) : (
              <div className="flex items-end gap-1 h-40">
                {daily.map((d) => (
                  <div key={d.date} className="flex-1 flex flex-col items-center gap-1 group relative">
                    <div className="w-full bg-blue-200 rounded-t hover:bg-blue-400 transition-colors"
                      style={{ height: `${(d.cost / maxCost) * 100}%`, minHeight: 2 }} />
                    <span className="text-[9px] text-gray-400 -rotate-45 origin-top-left w-10 truncate">
                      {d.date.slice(5)}
                    </span>
                    <div className="absolute -top-8 bg-gray-800 text-white text-[10px] px-2 py-1 rounded opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap">
                      ${d.cost.toFixed(3)} · {formatNumber(d.tokens)} tokens
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Per-model breakdown */}
          {report?.by_model && Object.keys(report.by_model).length > 0 && (
            <div className="bg-white border rounded-xl p-6">
              <h3 className="font-semibold text-sm text-gray-900 mb-4">By Model</h3>
              <div className="space-y-2">
                {Object.entries(report.by_model)
                  .sort(([, a], [, b]) => b.cost - a.cost)
                  .map(([model, stats]) => (
                    <div key={model} className="flex items-center gap-4 py-2 border-b last:border-0">
                      <code className="text-xs font-mono text-gray-700 w-48 truncate">{model}</code>
                      <div className="flex-1 bg-gray-100 rounded-full h-2">
                        <div className="bg-brand h-2 rounded-full"
                          style={{ width: `${(stats.cost / (report.total_cost || 1)) * 100}%` }} />
                      </div>
                      <span className="text-xs font-medium text-gray-700 w-16 text-right">${stats.cost.toFixed(2)}</span>
                      <span className="text-xs text-gray-400 w-24 text-right">{formatNumber(stats.tokens)} tok</span>
                      <span className="text-xs text-gray-400 w-16 text-right">{stats.requests} req</span>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function SummaryCard({ label, value, icon: Icon }: { label: string; value: string; icon: any }) {
  return (
    <div className="bg-white border rounded-xl p-4">
      <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
        <Icon size={12} /> {label}
      </div>
      <div className="text-xl font-bold text-gray-900">{value}</div>
    </div>
  );
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}
