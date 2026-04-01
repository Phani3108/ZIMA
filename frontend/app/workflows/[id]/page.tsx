"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft, CheckCircle2, XCircle, AlertTriangle, Clock,
  Loader2, Play, RotateCcw, MessageSquare, Send, ChevronDown,
} from "lucide-react";
import clsx from "clsx";
import { workflows } from "@/lib/api";

type Stage = {
  id: string;
  name: string;
  stage_index: number;
  status: string;
  agent_name: string;
  skill_id: string;
  prompt_id: string;
  output: { text: string; metadata?: Record<string, any> } | null;
  preview_type: string | null;
  preview_url: string | null;
  error: string | null;
  requires_approval: boolean;
  llm_used: string | null;
  started_at: string | null;
  completed_at: string | null;
};

type WorkflowDetail = {
  id: string;
  name: string;
  skill_id: string;
  template_id: string | null;
  status: string;
  current_stage_index: number;
  variables: Record<string, string>;
  created_at: string;
  updated_at: string;
  stages: Stage[];
};

const STATUS_ICON: Record<string, any> = {
  pending: Clock,
  in_progress: Loader2,
  awaiting_review: AlertTriangle,
  approved: CheckCircle2,
  needs_retry: XCircle,
};

const STATUS_COLOR: Record<string, string> = {
  pending: "text-gray-400 bg-gray-50 border-gray-200",
  in_progress: "text-blue-600 bg-blue-50 border-blue-200",
  awaiting_review: "text-amber-600 bg-amber-50 border-amber-200",
  approved: "text-green-600 bg-green-50 border-green-200",
  needs_retry: "text-red-600 bg-red-50 border-red-200",
};

export default function WorkflowDetailPage() {
  const params = useParams();
  const workflowId = params.id as string;

  const [wf, setWf] = useState<WorkflowDetail | null>(null);
  const [expandedStage, setExpandedStage] = useState<string | null>(null);
  const [comment, setComment] = useState("");
  const [editInstruction, setEditInstruction] = useState("");
  const [acting, setActing] = useState(false);
  const [msg, setMsg] = useState("");

  const load = useCallback(() => {
    workflows.get(workflowId).then(setWf);
  }, [workflowId]);

  useEffect(() => {
    load();
    // Poll every 5 seconds for active workflows
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, [load]);

  const handleApprove = async (stageId: string) => {
    setActing(true);
    try {
      const res = await workflows.approve(workflowId, stageId, comment);
      setWf(res);
      setComment("");
      setMsg("Stage approved!");
      setTimeout(() => setMsg(""), 3000);
    } catch (e: any) {
      setMsg(`Error: ${e.message}`);
    }
    setActing(false);
  };

  const handleReject = async (stageId: string) => {
    setActing(true);
    try {
      const res = await workflows.reject(workflowId, stageId, comment);
      setWf(res);
      setComment("");
      setMsg("Stage rejected — ready for retry.");
      setTimeout(() => setMsg(""), 3000);
    } catch (e: any) {
      setMsg(`Error: ${e.message}`);
    }
    setActing(false);
  };

  const handleRetry = async (stageId: string, llm?: string) => {
    setActing(true);
    try {
      await workflows.retry(workflowId, stageId, llm);
      setMsg("Retrying stage...");
      setTimeout(() => { setMsg(""); load(); }, 2000);
    } catch (e: any) {
      setMsg(`Error: ${e.message}`);
    }
    setActing(false);
  };

  const handleEdit = async (stageId: string) => {
    if (!editInstruction.trim()) return;
    setActing(true);
    try {
      await workflows.edit(workflowId, stageId, editInstruction);
      setEditInstruction("");
      setMsg("Editing in progress...");
      setTimeout(() => { setMsg(""); load(); }, 2000);
    } catch (e: any) {
      setMsg(`Error: ${e.message}`);
    }
    setActing(false);
  };

  const handleAdvance = async () => {
    setActing(true);
    try {
      await workflows.advance(workflowId);
      setMsg("Advancing...");
      setTimeout(() => { setMsg(""); load(); }, 2000);
    } catch (e: any) {
      setMsg(`Error: ${e.message}`);
    }
    setActing(false);
  };

  if (!wf) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="animate-spin text-gray-400" size={24} />
      </div>
    );
  }

  const progress = wf.stages.length > 0
    ? (wf.stages.filter((s) => s.status === "approved").length / wf.stages.length) * 100
    : 0;

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      {/* Header */}
      <Link href="/workflows" className="flex items-center gap-1 text-sm text-gray-500 hover:text-brand mb-4">
        <ArrowLeft size={14} /> Back to Workflows
      </Link>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">{wf.name}</h1>
          <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
            <span>Skill: {wf.skill_id}</span>
            {wf.template_id && <span>Template: {wf.template_id}</span>}
            <span>Created: {new Date(wf.created_at).toLocaleString()}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={clsx("px-3 py-1 rounded-full text-xs font-medium", STATUS_COLOR[wf.status] || STATUS_COLOR.pending)}>
            {wf.status.toUpperCase()}
          </span>
          {wf.status === "active" && (
            <button
              onClick={handleAdvance}
              disabled={acting}
              className="flex items-center gap-1 bg-brand text-white px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              <Play size={12} /> Advance
            </button>
          )}
        </div>
      </div>

      {/* Progress bar */}
      <div className="bg-gray-100 rounded-full h-2 mb-8 overflow-hidden">
        <div className="bg-brand h-full rounded-full transition-all" style={{ width: `${progress}%` }} />
      </div>

      {/* Toast */}
      {msg && (
        <div className="bg-gray-900 text-white text-sm px-4 py-2 rounded-xl mb-4 animate-pulse">
          {msg}
        </div>
      )}

      {/* Stage Timeline */}
      <div className="space-y-4">
        {wf.stages.map((stage, idx) => {
          const Icon = STATUS_ICON[stage.status] || Clock;
          const isExpanded = expandedStage === stage.id;
          const isCurrent = idx === wf.current_stage_index;

          return (
            <div
              key={stage.id}
              className={clsx(
                "border rounded-xl transition-all",
                isCurrent ? "border-brand shadow-sm" : "border-gray-200",
                isExpanded ? "bg-white" : "bg-white"
              )}
            >
              {/* Stage header */}
              <button
                onClick={() => setExpandedStage(isExpanded ? null : stage.id)}
                className="w-full flex items-center gap-3 p-4 text-left"
              >
                <div className={clsx("w-8 h-8 rounded-full flex items-center justify-center shrink-0 border", STATUS_COLOR[stage.status])}>
                  <Icon size={14} className={stage.status === "in_progress" ? "animate-spin" : ""} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h4 className="font-medium text-sm text-gray-900">{stage.name}</h4>
                    {stage.requires_approval && (
                      <span className="text-[10px] bg-amber-100 text-amber-600 px-1.5 py-0.5 rounded">Approval</span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-[11px] text-gray-500 mt-0.5">
                    <span>{stage.agent_name} agent</span>
                    {stage.llm_used && <span>&bull; {stage.llm_used}</span>}
                    {stage.completed_at && <span>&bull; {new Date(stage.completed_at).toLocaleString()}</span>}
                  </div>
                </div>
                <ChevronDown size={14} className={clsx("text-gray-400 transition-transform", isExpanded && "rotate-180")} />
              </button>

              {/* Expanded content */}
              {isExpanded && (
                <div className="px-4 pb-4 border-t">
                  {/* Error */}
                  {stage.error && (
                    <div className="mt-3 bg-red-50 text-red-700 text-xs px-3 py-2 rounded-lg">
                      {stage.error}
                    </div>
                  )}

                  {/* Output */}
                  {stage.output && (
                    <div className="mt-3">
                      <h5 className="text-xs font-semibold text-gray-500 uppercase mb-2">Output</h5>

                      {/* Embedded Preview */}
                      {stage.preview_type === "html" && stage.preview_url && (
                        <iframe
                          src={stage.preview_url}
                          className="w-full h-96 border rounded-lg mb-3"
                          sandbox="allow-same-origin"
                        />
                      )}
                      {stage.preview_type === "image" && stage.preview_url && (
                        <img src={stage.preview_url} className="max-w-full rounded-lg mb-3" alt="Preview" />
                      )}
                      {stage.preview_type === "canva" && stage.preview_url && (
                        <iframe
                          src={stage.preview_url}
                          className="w-full h-96 border rounded-lg mb-3"
                          allow="fullscreen"
                        />
                      )}

                      {/* Text output */}
                      <div className="bg-gray-50 rounded-lg p-3 text-sm text-gray-700 whitespace-pre-wrap max-h-96 overflow-y-auto font-mono text-xs">
                        {typeof stage.output === "object" ? stage.output.text : String(stage.output)}
                      </div>

                      {/* Edit via chat */}
                      <div className="flex gap-2 mt-3">
                        <input
                          type="text"
                          placeholder="Make it more casual, add a CTA..."
                          value={editInstruction}
                          onChange={(e) => setEditInstruction(e.target.value)}
                          onKeyDown={(e) => { if (e.key === "Enter") handleEdit(stage.id); }}
                          className="flex-1 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand"
                        />
                        <button
                          onClick={() => handleEdit(stage.id)}
                          disabled={acting || !editInstruction.trim()}
                          className="bg-gray-900 text-white px-3 py-2 rounded-lg text-sm disabled:opacity-50"
                        >
                          <Send size={14} />
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Approval actions */}
                  {stage.status === "awaiting_review" && (
                    <div className="mt-4 space-y-3">
                      <textarea
                        placeholder="Comment (optional)..."
                        value={comment}
                        onChange={(e) => setComment(e.target.value)}
                        rows={2}
                        className="w-full border rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-brand"
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleApprove(stage.id)}
                          disabled={acting}
                          className="flex items-center gap-1 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50"
                        >
                          <CheckCircle2 size={14} /> Approve
                        </button>
                        <button
                          onClick={() => handleReject(stage.id)}
                          disabled={acting}
                          className="flex items-center gap-1 bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50"
                        >
                          <XCircle size={14} /> Reject
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Retry actions */}
                  {stage.status === "needs_retry" && (
                    <div className="mt-4 flex gap-2">
                      <button
                        onClick={() => handleRetry(stage.id)}
                        disabled={acting}
                        className="flex items-center gap-1 bg-brand hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50"
                      >
                        <RotateCcw size={14} /> Retry
                      </button>
                      <button
                        onClick={() => handleRetry(stage.id, "claude")}
                        disabled={acting}
                        className="flex items-center gap-1 border border-gray-300 text-gray-600 px-3 py-2 rounded-lg text-xs hover:bg-gray-50 disabled:opacity-50"
                      >
                        Retry with Claude
                      </button>
                      <button
                        onClick={() => handleRetry(stage.id, "openai")}
                        disabled={acting}
                        className="flex items-center gap-1 border border-gray-300 text-gray-600 px-3 py-2 rounded-lg text-xs hover:bg-gray-50 disabled:opacity-50"
                      >
                        Retry with GPT-4
                      </button>
                      <button
                        onClick={() => handleRetry(stage.id, "gemini")}
                        disabled={acting}
                        className="flex items-center gap-1 border border-gray-300 text-gray-600 px-3 py-2 rounded-lg text-xs hover:bg-gray-50 disabled:opacity-50"
                      >
                        Retry with Gemini
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
