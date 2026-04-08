"use client";

import { useState, useEffect } from "react";
import { Shield, Loader2, CheckCircle, XCircle, Clock, Inbox, FileCheck, BarChart2 } from "lucide-react";
import clsx from "clsx";
import { useBackend } from "@/lib/useBackend";
import DemoBanner from "@/components/DemoBanner";
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

/* ─── Demo Data ─────────────────────────────────────────────────── */

const DEMO_APPROVALS: Approval[] = [
  {
    stage_id: "demo-stg-1",
    workflow_id: "demo-wf-1",
    workflow_name: "Q3 Product Launch — LinkedIn Post",
    stage_name: "Manager Approval",
    agent_name: "copy",
    status: "awaiting_review",
    output: {
      text: "🚀 Exciting news! After months of building in stealth, we're thrilled to unveil our next-gen AI campaign builder.\n\nWhat makes it different:\n→ Writes, reviews & optimizes automatically\n→ 8 specialized AI agents working as a team\n→ Brand voice consistency across every channel\n\nEarly adopters are seeing 3x faster time-to-publish.\n\nReady to try it? Link in comments 👇\n\n#ProductLaunch #MarTech #AI #ContentMarketing",
    },
    preview_type: "text",
    started_at: "2026-04-08T09:30:00Z",
  },
  {
    stage_id: "demo-stg-2",
    workflow_id: "demo-wf-2",
    workflow_name: "April Newsletter — Email Sequence",
    stage_name: "Content Approval",
    agent_name: "copy",
    status: "awaiting_review",
    output: {
      text: "Subject: April Highlights — What We Shipped & What's Coming\n\nHi {{first_name}},\n\nApril was a big month for us. Here's the TL;DR:\n\n✅ Launched AI Campaign Builder v2\n✅ Added 3 new content templates\n✅ Improved SEO scoring by 40%\n\nWhat's next: We're working on approval chain workflows so your team leads can review content before it goes live.\n\nStay tuned,\nThe Zeta Team",
    },
    preview_type: "text",
    started_at: "2026-04-08T08:15:00Z",
  },
  {
    stage_id: "demo-stg-3",
    workflow_id: "demo-wf-3",
    workflow_name: "Competitive Analysis — MarTech Landscape",
    stage_name: "Strategy Review",
    agent_name: "competitive_intel",
    status: "awaiting_review",
    output: {
      text: "## Competitive Landscape: MarTech Q2 2026\n\n**Key Findings:**\n1. Competitor A raised $25M — expanding into AI content generation\n2. Competitor B launched an agent-based workflow — similar to our approach\n3. Market gap: No player offers end-to-end approval chains with named routing\n\n**Recommendation:** Double down on approval workflows as a differentiator. Our configurable per-team routing is unique in market.",
    },
    preview_type: "text",
    started_at: "2026-04-07T16:00:00Z",
  },
];

export default function FutureApprovalsPage() {
  const { online } = useBackend();
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState<string | null>(null);
  const [comment, setComment] = useState<Record<string, string>>({});

  const showDemo = !online;

  const load = async () => {
    setLoading(true);
    try {
      if (online) {
        const data = await futureApprovals.mine();
        setApprovals(data);
      }
    } catch {
      // handled
    }
    setLoading(false);
  };

  useEffect(() => {
    if (online) {
      load();
    } else {
      setLoading(false);
    }
  }, [online]);

  const displayApprovals = showDemo ? DEMO_APPROVALS : approvals;

  const decide = async (workflowId: string, stageId: string, decision: "approve" | "reject") => {
    if (showDemo) return;
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
    <div className="max-w-3xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
        <Shield className="w-5 h-5" />
        My Approvals
      </h1>
      <p className="text-gray-500 mt-1 text-sm mb-6">
        Review and approve content from your AI agents before it goes live.
      </p>

      {showDemo && (
        <DemoBanner
          feature="Approvals"
          steps={[
            "Start the backend and configure approval routing in Teams settings",
            "AI agents will route completed content to the assigned approver",
            "Review the output, add optional feedback, then approve or reject",
          ]}
        />
      )}

      {/* Stats */}
      {showDemo && (
        <div className="grid grid-cols-3 gap-3 mb-6">
          <div className="bg-white border rounded-xl p-3">
            <div className="flex items-center gap-1.5 mb-1">
              <Inbox size={13} className="text-gray-400" />
              <span className="text-[11px] text-gray-500 uppercase tracking-wider">Pending</span>
            </div>
            <div className="text-xl font-bold text-amber-600">{DEMO_APPROVALS.length}</div>
          </div>
          <div className="bg-white border rounded-xl p-3">
            <div className="flex items-center gap-1.5 mb-1">
              <FileCheck size={13} className="text-gray-400" />
              <span className="text-[11px] text-gray-500 uppercase tracking-wider">Approved Today</span>
            </div>
            <div className="text-xl font-bold text-green-600">5</div>
          </div>
          <div className="bg-white border rounded-xl p-3">
            <div className="flex items-center gap-1.5 mb-1">
              <BarChart2 size={13} className="text-gray-400" />
              <span className="text-[11px] text-gray-500 uppercase tracking-wider">Avg Review Time</span>
            </div>
            <div className="text-xl font-bold text-blue-600">12m</div>
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      ) : displayApprovals.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <CheckCircle className="w-8 h-8 mx-auto mb-2" />
          <div>All caught up — no pending approvals.</div>
        </div>
      ) : (
        <div className="space-y-4">
          {displayApprovals.map((a) => (
            <div key={a.stage_id} className="bg-white border rounded-xl p-4 shadow-sm">
              {/* Header */}
              <div className="flex items-center justify-between mb-2">
                <div>
                  <div className="font-medium text-gray-800">{a.stage_name}</div>
                  <div className="text-xs text-gray-400">
                    {a.workflow_name} • by <span className="font-medium">{a.agent_name}</span> agent
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
                  disabled={showDemo}
                />
                <button
                  onClick={() => decide(a.workflow_id, a.stage_id, "approve")}
                  disabled={acting === a.stage_id || showDemo}
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
                  disabled={acting === a.stage_id || showDemo}
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

      {showDemo && (
        <p className="text-[10px] text-gray-400 text-center mt-6">
          Mock data — will be replaced with real approval items once workflows are running.
        </p>
      )}
    </div>
  );
}
