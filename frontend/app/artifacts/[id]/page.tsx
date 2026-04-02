"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft, Share2, MessageSquare, History, Copy, Download,
  Clock, User, Tag, CheckCircle2, XCircle, Send, Link2,
  Loader2, FileText,
} from "lucide-react";
import { artifacts } from "@/lib/api";
import { useBackend } from "@/lib/useBackend";
import OfflineBanner from "@/components/OfflineBanner";

type Comment = {
  id: string;
  author: string;
  body: string;
  created_at: string;
  is_external: boolean;
};

const DEMO_CONTENT = `# Q3 Product Launch Blog Post

## Introduction

Announcing our latest product update — a game-changing platform for modern marketing teams...

## Key Features

- **AI-Powered Content Generation**: Create on-brand content in seconds
- **Multi-Channel Distribution**: Publish across email, social, and web simultaneously
- **Real-Time Analytics**: Track engagement metrics as they happen
- **Team Collaboration**: Built-in review workflows with external approval gates

## Why It Matters

Marketing teams spend 60% of their time on repetitive tasks. Our platform reduces that to under 10%, freeing teams to focus on strategy and creativity.

## Call to Action

Ready to transform your marketing workflow? [Start your free trial →](#)

---
*Tags: blog, product-launch, Q3*
`;

const DEMO_COMMENTS: Comment[] = [
  { id: "c1", author: "Sarah (Brand Lead)", body: "Great structure! Can we add more data points in the 'Why It Matters' section?", created_at: "2025-01-17T14:30:00Z", is_external: false },
  { id: "c2", author: "[External] Client - Jane", body: "Love the tone. Please adjust the CTA to mention the product name specifically.", created_at: "2025-01-18T09:15:00Z", is_external: true },
  { id: "c3", author: "AI Content Agent", body: "Updated CTA based on client feedback. Version 3 created.", created_at: "2025-01-18T10:00:00Z", is_external: false },
];

export default function ArtifactDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { online } = useBackend();
  const [artifact, setArtifact] = useState<any>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"content" | "comments" | "versions">("content");
  const [newComment, setNewComment] = useState("");
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!online) {
      setArtifact({
        id,
        title: "Q3 Product Launch Blog Post",
        content: DEMO_CONTENT,
        content_type: "markdown",
        version: 3,
        tags: ["blog", "product-launch"],
        created_by: "content-strategist",
        created_at: "2025-01-15T10:30:00Z",
        updated_at: "2025-01-18T14:20:00Z",
        team_id: "demo",
      });
      setComments(DEMO_COMMENTS);
      setLoading(false);
      return;
    }
    Promise.all([
      artifacts.get(id).catch(() => null),
      artifacts.comments(id).catch(() => ({ comments: [] })),
    ]).then(([art, cmt]) => {
      setArtifact(art);
      setComments(cmt?.comments || []);
      setLoading(false);
    });
  }, [id, online]);

  const handleCopy = () => {
    if (artifact?.content) {
      navigator.clipboard.writeText(artifact.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleShare = async () => {
    if (!online) {
      setShareUrl(`${window.location.origin}/review/demo-token-abc123`);
      return;
    }
    try {
      const res = await artifacts.createShareLink(id, { allow_comments: true, allow_approve: true });
      setShareUrl(`${window.location.origin}/review/${res.token}`);
    } catch {
      // fallback
    }
  };

  const handleAddComment = async () => {
    if (!newComment.trim()) return;
    if (online) {
      try {
        await artifacts.addComment(id, { author: "You", body: newComment });
      } catch {}
    }
    setComments([
      ...comments,
      { id: `c-${Date.now()}`, author: "You", body: newComment, created_at: new Date().toISOString(), is_external: false },
    ]);
    setNewComment("");
  };

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-6 py-16 text-center">
        <Loader2 size={24} className="animate-spin mx-auto text-gray-400" />
      </div>
    );
  }

  if (!artifact) {
    return (
      <div className="max-w-5xl mx-auto px-6 py-8">
        <Link href="/artifacts" className="text-blue-600 hover:underline text-sm flex items-center gap-1 mb-4">
          <ArrowLeft size={14} /> Back to Library
        </Link>
        <OfflineBanner title="Artifact Not Found" />
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      {/* Header */}
      <Link href="/artifacts" className="text-blue-600 hover:underline text-sm flex items-center gap-1 mb-4">
        <ArrowLeft size={14} /> Back to Library
      </Link>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{artifact.title}</h1>
          <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
            <span className="flex items-center gap-1"><User size={14} /> {artifact.created_by}</span>
            <span className="flex items-center gap-1"><Clock size={14} /> {new Date(artifact.updated_at).toLocaleDateString()}</span>
            <span className="bg-gray-100 px-2 py-0.5 rounded-full text-xs">v{artifact.version}</span>
          </div>
          <div className="flex gap-1.5 mt-2">
            {artifact.tags?.map((t: string) => (
              <span key={t} className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full flex items-center gap-1">
                <Tag size={10} /> {t}
              </span>
            ))}
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={handleCopy} className="flex items-center gap-1.5 px-3 py-2 border rounded-xl text-sm hover:bg-gray-50 transition-colors">
            {copied ? <CheckCircle2 size={14} className="text-green-500" /> : <Copy size={14} />}
            {copied ? "Copied" : "Copy"}
          </button>
          <button onClick={handleShare} className="flex items-center gap-1.5 px-3 py-2 bg-blue-600 text-white rounded-xl text-sm hover:bg-blue-700 transition-colors">
            <Share2 size={14} /> Share for Review
          </button>
        </div>
      </div>

      {/* Share Link Banner */}
      {shareUrl && (
        <div className="mb-6 bg-green-50 border border-green-200 rounded-xl p-4 flex items-center justify-between">
          <div className="flex items-center gap-2 text-green-700 text-sm">
            <Link2 size={16} />
            <span>Share link created!</span>
          </div>
          <div className="flex items-center gap-2">
            <code className="text-xs bg-white border px-3 py-1 rounded-lg text-green-800 max-w-md truncate">
              {shareUrl}
            </code>
            <button
              onClick={() => { navigator.clipboard.writeText(shareUrl); }}
              className="text-sm text-green-700 hover:underline"
            >
              Copy
            </button>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b mb-6">
        <div className="flex gap-6">
          {[
            { key: "content" as const, icon: FileText, label: "Content" },
            { key: "comments" as const, icon: MessageSquare, label: `Comments (${comments.length})` },
            { key: "versions" as const, icon: History, label: "Version History" },
          ].map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`flex items-center gap-1.5 pb-3 border-b-2 text-sm font-medium transition-colors ${
                tab === t.key ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              <t.icon size={14} /> {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content Tab */}
      {tab === "content" && (
        <div className="bg-white border rounded-2xl p-6">
          <pre className="whitespace-pre-wrap text-sm text-gray-800 font-mono leading-relaxed">
            {artifact.content}
          </pre>
        </div>
      )}

      {/* Comments Tab */}
      {tab === "comments" && (
        <div className="space-y-4">
          {comments.length === 0 ? (
            <p className="text-center py-8 text-gray-400 text-sm">No comments yet.</p>
          ) : (
            comments.map((c) => (
              <div
                key={c.id}
                className={`border rounded-xl p-4 ${c.is_external ? "bg-amber-50 border-amber-200" : "bg-white"}`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-900">
                    {c.author}
                    {c.is_external && (
                      <span className="ml-2 text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">External</span>
                    )}
                  </span>
                  <span className="text-xs text-gray-400">{new Date(c.created_at).toLocaleString()}</span>
                </div>
                <p className="text-sm text-gray-700">{c.body}</p>
              </div>
            ))
          )}
          {/* Add comment */}
          <div className="flex gap-2 mt-4">
            <input
              type="text"
              placeholder="Add a comment..."
              value={newComment}
              onChange={(e) => setNewComment(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAddComment()}
              className="flex-1 border rounded-xl px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={handleAddComment}
              disabled={!newComment.trim()}
              className="px-4 py-2 bg-blue-600 text-white rounded-xl text-sm hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              <Send size={14} />
            </button>
          </div>
        </div>
      )}

      {/* Versions Tab */}
      {tab === "versions" && (
        <div className="space-y-3">
          {[
            { version: 3, by: "AI Content Agent", date: "2025-01-18T14:20:00Z", note: "Updated CTA per client feedback" },
            { version: 2, by: "content-strategist", date: "2025-01-17T10:00:00Z", note: "Added data points and refined structure" },
            { version: 1, by: "blog-writer-agent", date: "2025-01-15T10:30:00Z", note: "Initial draft from workflow" },
          ].map((v) => (
            <div key={v.version} className="flex items-center gap-4 border rounded-xl p-4 bg-white">
              <div className="w-10 h-10 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center font-bold text-sm">
                v{v.version}
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">{v.note}</p>
                <p className="text-xs text-gray-400">{v.by} · {new Date(v.date).toLocaleString()}</p>
              </div>
              {v.version === artifact.version && (
                <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">Current</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
