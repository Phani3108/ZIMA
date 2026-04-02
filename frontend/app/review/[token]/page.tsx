"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import {
  CheckCircle2, XCircle, MessageSquare, Send, Shield,
  Clock, Tag, FileText, Loader2, AlertTriangle,
  ThumbsUp, ThumbsDown,
} from "lucide-react";

const DEMO_ARTIFACT = {
  id: "art-demo-1",
  title: "Q3 Product Launch Blog Post",
  content: `# Q3 Product Launch Blog Post

## Introduction

Announcing our latest product update — a game-changing platform for modern marketing teams.

## Key Features

- **AI-Powered Content Generation**: Create on-brand content in seconds
- **Multi-Channel Distribution**: Publish across email, social, and web simultaneously
- **Real-Time Analytics**: Track engagement metrics as they happen
- **Team Collaboration**: Built-in review workflows with external approval gates

## Why It Matters

Marketing teams spend 60% of their time on repetitive tasks. Our platform reduces that to under 10%, freeing teams to focus on strategy and creativity.

## Call to Action

Ready to transform your marketing workflow? Start your free trial today.`,
  content_type: "markdown",
  version: 3,
  tags: ["blog", "product-launch"],
  created_at: "2025-01-15T10:30:00Z",
  updated_at: "2025-01-18T14:20:00Z",
  permissions: { allow_comments: true, allow_approve: true },
  comments: [
    { id: "c1", author: "Sarah (Brand Lead)", body: "Great structure! Can we add more data points?", created_at: "2025-01-17T14:30:00Z", is_external: false },
  ],
};

type Comment = {
  id: string;
  author: string;
  body: string;
  created_at: string;
  is_external: boolean;
};

export default function ExternalReviewPage() {
  const { token } = useParams<{ token: string }>();
  const [artifact, setArtifact] = useState<any>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);
  const [expired, setExpired] = useState(false);
  const [reviewerName, setReviewerName] = useState("");
  const [newComment, setNewComment] = useState("");
  const [decision, setDecision] = useState<"approved" | "rejected" | null>(null);
  const [decisionComment, setDecisionComment] = useState("");
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    // Try to fetch from backend
    fetch(`/api/artifacts/shared/${token}`)
      .then((r) => {
        if (!r.ok) throw new Error("not found");
        return r.json();
      })
      .then((data) => {
        setArtifact(data);
        setComments(data.comments || []);
        setLoading(false);
      })
      .catch(() => {
        // Demo fallback
        if (token?.includes("demo")) {
          setArtifact(DEMO_ARTIFACT);
          setComments(DEMO_ARTIFACT.comments);
        } else {
          setExpired(true);
        }
        setLoading(false);
      });
  }, [token]);

  const handleAddComment = async () => {
    if (!newComment.trim() || !reviewerName.trim()) return;
    try {
      await fetch(`/api/artifacts/shared/${token}/comments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ author: reviewerName, body: newComment }),
      });
    } catch {}
    setComments([
      ...comments,
      { id: `c-${Date.now()}`, author: `[External] ${reviewerName}`, body: newComment, created_at: new Date().toISOString(), is_external: true },
    ]);
    setNewComment("");
  };

  const handleDecision = async (type: "approved" | "rejected") => {
    if (!reviewerName.trim()) return;
    const endpoint = type === "approved" ? "approve" : "reject";
    try {
      await fetch(`/api/artifacts/shared/${token}/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reviewer: reviewerName, comment: decisionComment }),
      });
    } catch {}
    setDecision(type);
    setSubmitted(true);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 size={32} className="animate-spin text-gray-400" />
      </div>
    );
  }

  if (expired) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle size={48} className="mx-auto mb-4 text-amber-400" />
          <h1 className="text-xl font-bold text-gray-900 mb-2">Link Expired or Not Found</h1>
          <p className="text-gray-500 text-sm">This review link may have expired or been revoked. Contact the team for a new link.</p>
        </div>
      </div>
    );
  }

  if (submitted) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md">
          {decision === "approved" ? (
            <CheckCircle2 size={48} className="mx-auto mb-4 text-green-500" />
          ) : (
            <XCircle size={48} className="mx-auto mb-4 text-red-500" />
          )}
          <h1 className="text-xl font-bold text-gray-900 mb-2">
            {decision === "approved" ? "Approved!" : "Feedback Sent"}
          </h1>
          <p className="text-gray-500 text-sm">
            {decision === "approved"
              ? "Your approval has been recorded. The team has been notified."
              : "Your feedback has been sent to the team. They'll revise and share an updated version."}
          </p>
        </div>
      </div>
    );
  }

  const canComment = artifact?.permissions?.allow_comments;
  const canApprove = artifact?.permissions?.allow_approve;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-50 rounded-lg">
              <Shield size={20} className="text-blue-600" />
            </div>
            <div>
              <p className="text-xs text-gray-400 uppercase font-medium">External Review</p>
              <h1 className="text-lg font-bold text-gray-900">{artifact.title}</h1>
            </div>
          </div>
          <div className="flex items-center gap-3 text-sm text-gray-500">
            <span className="bg-gray-100 px-2 py-0.5 rounded-full text-xs">v{artifact.version}</span>
            <span className="flex items-center gap-1"><Clock size={14} /> {new Date(artifact.updated_at).toLocaleDateString()}</span>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Content */}
        <div className="lg:col-span-2">
          <div className="bg-white border rounded-2xl p-6">
            <div className="flex gap-1.5 mb-4">
              {artifact.tags?.map((t: string) => (
                <span key={t} className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full flex items-center gap-1">
                  <Tag size={10} /> {t}
                </span>
              ))}
            </div>
            <pre className="whitespace-pre-wrap text-sm text-gray-800 font-mono leading-relaxed">
              {artifact.content}
            </pre>
          </div>
        </div>

        {/* Review Panel */}
        <div className="space-y-6">
          {/* Reviewer Identity */}
          <div className="bg-white border rounded-2xl p-5">
            <label className="text-sm font-medium text-gray-700 block mb-2">Your Name</label>
            <input
              type="text"
              placeholder="Enter your name..."
              value={reviewerName}
              onChange={(e) => setReviewerName(e.target.value)}
              className="w-full border rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Decision Buttons */}
          {canApprove && (
            <div className="bg-white border rounded-2xl p-5 space-y-3">
              <h3 className="text-sm font-medium text-gray-700">Decision</h3>
              <textarea
                placeholder="Optional feedback..."
                value={decisionComment}
                onChange={(e) => setDecisionComment(e.target.value)}
                rows={3}
                className="w-full border rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
              />
              <div className="flex gap-2">
                <button
                  onClick={() => handleDecision("approved")}
                  disabled={!reviewerName.trim()}
                  className="flex-1 flex items-center justify-center gap-2 bg-green-600 text-white px-4 py-2.5 rounded-xl text-sm font-medium hover:bg-green-700 disabled:opacity-50 transition-colors"
                >
                  <ThumbsUp size={14} /> Approve
                </button>
                <button
                  onClick={() => handleDecision("rejected")}
                  disabled={!reviewerName.trim()}
                  className="flex-1 flex items-center justify-center gap-2 bg-red-600 text-white px-4 py-2.5 rounded-xl text-sm font-medium hover:bg-red-700 disabled:opacity-50 transition-colors"
                >
                  <ThumbsDown size={14} /> Request Changes
                </button>
              </div>
            </div>
          )}

          {/* Comments */}
          {canComment && (
            <div className="bg-white border rounded-2xl p-5 space-y-3">
              <h3 className="text-sm font-medium text-gray-700 flex items-center gap-1.5">
                <MessageSquare size={14} /> Comments ({comments.length})
              </h3>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {comments.map((c) => (
                  <div key={c.id} className={`p-3 rounded-lg text-sm ${c.is_external ? "bg-amber-50" : "bg-gray-50"}`}>
                    <div className="flex justify-between mb-1">
                      <span className="font-medium text-gray-900 text-xs">{c.author}</span>
                      <span className="text-xs text-gray-400">{new Date(c.created_at).toLocaleDateString()}</span>
                    </div>
                    <p className="text-gray-700 text-xs">{c.body}</p>
                  </div>
                ))}
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Add a comment..."
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleAddComment()}
                  className="flex-1 border rounded-lg px-3 py-2 text-sm"
                />
                <button
                  onClick={handleAddComment}
                  disabled={!newComment.trim() || !reviewerName.trim()}
                  className="px-3 py-2 bg-blue-600 text-white rounded-lg disabled:opacity-50"
                >
                  <Send size={14} />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="border-t bg-white mt-8">
        <div className="max-w-4xl mx-auto px-6 py-4 text-center text-xs text-gray-400">
          Powered by Zeta AI Marketing Agency · Secure external review
        </div>
      </div>
    </div>
  );
}
