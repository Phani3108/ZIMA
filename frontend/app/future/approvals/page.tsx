"use client";

import { useState, useEffect } from "react";
import { Shield, Loader2, CheckCircle, XCircle, Clock } from "lucide-react";
import clsx from "clsx";
import { futureApprovals } from "@/lib/api";

type Approval = {
  stage_id: string;
  workflow_id: string;
  workflow_name: string;
  stage_name: string;
  agent_name: string;
  status: string;
  output: { text?: string; metadata?: Record<string, unknown> } | null;
  preview_type: string | null;
  started_at: string | null;
};

export default function FutureApprovalsPage() {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState<string | null>(null);
  const [comment, setComment] = useState<Record<string, string>>({});

  const load = async () => {
    setLoading(true);
    try {
      const data = await futureApprovals.mine();
      setApprovals(data);
    } catch {
      // handled
    }
    setLoading(false);
  };

  useEffect(() => {
    load();
  }, []);

  const decide = async (workflowId: string, stageId: string, decision: "approve" | "reject") => {
    setActing(stageId);
    try {
      const { workflows } = await import("@/lib/api");
      if (decision === "approve") {
        await workflows.approve(workflowId, stageId, comment[stageId] || "");
      } else {
        await workflows.reject(workflowId, stageId, comment[stageId] || "");
      }
      await load();
    } catch {
      // handled
    }
    setActing(null);
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-6">
      <h1 className="text-xl font-semibold text-gray-800 mb-1 flex items-center gap-2">
        <Shield className="w-5 h-5" />
        My Approvals
      </h1>
      <p className="text-sm text-gray-500 mb-6">
        Content awaiting your review and approval.
      </p>

      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      ) : approvals.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <CheckCircle className="w-8 h-8 mx-auto mb-2" />
          <div>All caught up — no pending approvals.</div>
        </div>
      ) : (
        <div className="space-y-4">
          {approvals.map((a) => (
            <div key={a.stage_id} className="bg-white border rounded-xl p-4 shadow-sm">
              {/* Header */}
              <div className="flex items-center justify-between mb-2">
                <div>
                  <div className="font-medium text-gray-800">{a.stage_name}</div>
                  <div className="text-xs text-gray-400">
                    {a.workflow_name} • by {a.agent_name} agent
                  </div>
                </div>
                <div className="flex items-center gap-1 text-xs text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full">
                  <Clock className="w-3 h-3" />
                  Awaiting Review
                </div>
              </div>

              {/* Output preview */}
              {a.output?.text && (
                <div className="bg-gray-50 border rounded-lg p-3 mb-3 text-sm text-gray-700 whitespace-pre-wrap max-h-48 overflow-y-auto">
                  {a.output.text}
                </div>
              )}

              {/* Started at */}
              {a.started_at && (
                <div className="text-xs text-gray-400 mb-3">
                  Started: {new Date(a.started_at).toLocaleString()}
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-2 items-center border-t pt-3">
                <input
                  value={comment[a.stage_id] || ""}
                  onChange={(e) =>
                    setComment((prev) => ({ ...prev, [a.stage_id]: e.target.value }))
                  }
                  placeholder="Optional comment..."
                  className="flex-1 text-sm border rounded px-2 py-1"
                />
                <button
                  onClick={() => decide(a.workflow_id, a.stage_id, "approve")}
                  disabled={acting === a.stage_id}
                  className="flex items-center gap-1 px-3 py-1.5 bg-green-600 text-white text-sm rounded hover:bg-green-700 disabled:opacity-50"
                >
                  {acting === a.stage_id ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <CheckCircle className="w-4 h-4" />
                  )}
                  Approve
                </button>
                <button
                  onClick={() => decide(a.workflow_id, a.stage_id, "reject")}
                  disabled={acting === a.stage_id}
                  className="flex items-center gap-1 px-3 py-1.5 bg-red-500 text-white text-sm rounded hover:bg-red-600 disabled:opacity-50"
                >
                  <XCircle className="w-4 h-4" />
                  Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
