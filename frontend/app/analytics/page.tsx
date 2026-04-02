"use client";

import { useEffect, useState } from "react";
import { BarChart2, TrendingUp, Target, Layers, WifiOff } from "lucide-react";

type Output = {
  id: string;
  brief: string;
  text: string;
  channel: string;
  iterations_needed: number;
  approved_at: string;
  campaign_id: string;
};

type Stats = {
  total_approved_outputs: number;
  avg_iterations_to_approval: number;
};

export default function AnalyticsPage() {
  const [outputs, setOutputs] = useState<Output[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [backendOnline, setBackendOnline] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch("/api/analytics/outputs").then((r) => { if (!r.ok) throw new Error(); return r.json(); }).catch(() => null),
      fetch("/api/analytics/stats").then((r) => { if (!r.ok) throw new Error(); return r.json(); }).catch(() => null),
    ]).then(([o, s]) => {
      if (o === null && s === null) {
        setBackendOnline(false);
      } else {
        if (o) setOutputs(o);
        if (s) setStats(s);
      }
    });
  }, []);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-xl font-semibold text-gray-800 mb-6">Analytics</h1>

      {/* Offline state */}
      {!backendOnline && (
        <div className="text-center py-12">
          <WifiOff size={40} className="mx-auto mb-3 text-amber-400" />
          <p className="text-gray-600 font-medium mb-1">Backend Offline</p>
          <p className="text-sm text-gray-400 max-w-md mx-auto mb-8">
            Analytics tracks all approved outputs, campaign performance, and agent efficiency.
            Deploy the backend to see real data.
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-2xl mx-auto">
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 text-left">
              <BarChart2 size={20} className="text-blue-500 mb-2" />
              <div className="text-sm font-medium text-gray-700">Output Tracking</div>
              <p className="text-xs text-gray-400 mt-1">Every approved draft with iteration counts</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 text-left">
              <TrendingUp size={20} className="text-green-500 mb-2" />
              <div className="text-sm font-medium text-gray-700">Performance Trends</div>
              <p className="text-xs text-gray-400 mt-1">Approval rates and quality over time</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 text-left">
              <Target size={20} className="text-purple-500 mb-2" />
              <div className="text-sm font-medium text-gray-700">Channel Breakdown</div>
              <p className="text-xs text-gray-400 mt-1">Performance by channel: blog, social, email</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 text-left">
              <Layers size={20} className="text-amber-500 mb-2" />
              <div className="text-sm font-medium text-gray-700">Campaign Reports</div>
              <p className="text-xs text-gray-400 mt-1">Cross-campaign analytics and ROI</p>
            </div>
          </div>
        </div>
      )}

      {backendOnline && <>
      {/* Stats bar */}
      {stats && (
        <div className="grid grid-cols-2 gap-4 mb-8">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
            <div className="text-3xl font-bold text-brand">{stats.total_approved_outputs}</div>
            <div className="text-sm text-gray-500 mt-1">Approved outputs</div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
            <div className="text-3xl font-bold text-gray-700">{stats.avg_iterations_to_approval}</div>
            <div className="text-sm text-gray-500 mt-1">Avg iterations to approval</div>
          </div>
        </div>
      )}

      {/* Output table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
            <tr>
              <th className="px-4 py-3 text-left">Brief</th>
              <th className="px-4 py-3 text-left">Channel</th>
              <th className="px-4 py-3 text-center">Iterations</th>
              <th className="px-4 py-3 text-left">Approved</th>
            </tr>
          </thead>
          <tbody>
            {outputs.map((o) => (
              <>
                <tr
                  key={o.id}
                  className="border-t border-gray-100 hover:bg-gray-50 cursor-pointer"
                  onClick={() => setExpanded(expanded === o.id ? null : o.id)}
                >
                  <td className="px-4 py-3 text-gray-700 max-w-xs truncate">{o.brief}</td>
                  <td className="px-4 py-3 text-gray-500">{o.channel || "—"}</td>
                  <td className="px-4 py-3 text-center text-gray-500">{o.iterations_needed}</td>
                  <td className="px-4 py-3 text-gray-400 text-xs">{o.approved_at?.slice(0, 16)}</td>
                </tr>
                {expanded === o.id && (
                  <tr key={`${o.id}-expanded`} className="bg-blue-50 border-t border-blue-100">
                    <td colSpan={4} className="px-4 py-3">
                      <p className="text-sm text-gray-700 whitespace-pre-wrap">{o.text}</p>
                    </td>
                  </tr>
                )}
              </>
            ))}
            {outputs.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-gray-400 text-sm">
                  No approved outputs yet. Approve some drafts to see them here.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      </>}
    </div>
  );
}
