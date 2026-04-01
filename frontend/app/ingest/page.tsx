"use client";

import { useState, useRef } from "react";
import { Upload, Link, BookOpen, MessageSquare, CheckCircle, Loader2, AlertCircle } from "lucide-react";
import clsx from "clsx";

type Tab = "file" | "url" | "confluence" | "teams_chat";
type Job = { job_id: string; status: string; source: string };

export default function IngestPage() {
  const [tab, setTab] = useState<Tab>("file");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [url, setUrl] = useState("");
  const [confluenceId, setConfluenceId] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const chatRef = useRef<HTMLInputElement>(null);

  const uploadFile = async (file: File, endpoint: string) => {
    setLoading(true);
    const form = new FormData();
    form.append("file", file);
    const r = await fetch(`/api/ingest/${endpoint}`, { method: "POST", body: form });
    const data = await r.json();
    setLoading(false);
    if (data.job_id) setJobs((j) => [{ job_id: data.job_id, status: "pending", source: file.name }, ...j]);
  };

  const submitUrl = async () => {
    if (!url.trim()) return;
    setLoading(true);
    const r = await fetch("/api/ingest/url", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    const data = await r.json();
    setLoading(false);
    if (data.job_id) {
      setJobs((j) => [{ job_id: data.job_id, status: "pending", source: url }, ...j]);
      setUrl("");
    }
  };

  const submitConfluence = async () => {
    if (!confluenceId.trim()) return;
    setLoading(true);
    const r = await fetch("/api/ingest/confluence", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ page_id: confluenceId }),
    });
    const data = await r.json();
    setLoading(false);
    if (data.job_id) {
      setJobs((j) => [{ job_id: data.job_id, status: "pending", source: `Confluence: ${confluenceId}` }, ...j]);
      setConfluenceId("");
    }
  };

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: "file", label: "File Upload", icon: <Upload size={14} /> },
    { id: "url", label: "URL", icon: <Link size={14} /> },
    { id: "confluence", label: "Confluence", icon: <BookOpen size={14} /> },
    { id: "teams_chat", label: "Teams Chat", icon: <MessageSquare size={14} /> },
  ];

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-xl font-semibold text-gray-800 mb-1">Knowledge Base Ingestion</h1>
      <p className="text-sm text-gray-500 mb-6">
        Ingest brand guidelines, process docs, URLs, or past conversations. Agents use this as grounding context.
      </p>

      {/* Tabs */}
      <div className="flex gap-1 border-b mb-6">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={clsx(
              "flex items-center gap-1.5 px-3 py-2 text-sm rounded-t-lg",
              tab === t.id ? "bg-white border border-b-white text-brand font-medium" : "text-gray-500 hover:text-gray-700"
            )}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        {tab === "file" && (
          <div>
            <p className="text-sm text-gray-600 mb-3">Supports PDF, DOCX, TXT. Max 20MB.</p>
            <div
              className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center cursor-pointer hover:border-brand hover:bg-blue-50 transition-colors"
              onClick={() => fileRef.current?.click()}
            >
              <Upload size={32} className="mx-auto text-gray-300 mb-2" />
              <p className="text-sm text-gray-500">Click to select or drag & drop a file</p>
              <input ref={fileRef} type="file" accept=".pdf,.docx,.txt,.md" className="hidden"
                onChange={(e) => e.target.files?.[0] && uploadFile(e.target.files[0], "file")} />
            </div>
          </div>
        )}

        {tab === "url" && (
          <div className="space-y-3">
            <p className="text-sm text-gray-600">Paste a public URL. The page will be scraped and ingested.</p>
            <input
              type="url"
              placeholder="https://yoursite.com/brand-guidelines"
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submitUrl()}
            />
            <button onClick={submitUrl} disabled={loading || !url.trim()}
              className="bg-brand hover:bg-blue-700 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-50">
              Ingest URL
            </button>
          </div>
        )}

        {tab === "confluence" && (
          <div className="space-y-3">
            <p className="text-sm text-gray-600">Enter a Confluence page ID to pull and ingest.</p>
            <input
              placeholder="e.g. 123456789"
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand"
              value={confluenceId}
              onChange={(e) => setConfluenceId(e.target.value)}
            />
            <button onClick={submitConfluence} disabled={loading || !confluenceId.trim()}
              className="bg-brand hover:bg-blue-700 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-50">
              Pull Page
            </button>
          </div>
        )}

        {tab === "teams_chat" && (
          <div>
            <p className="text-sm text-gray-600 mb-3">
              Export a Teams chat as JSON (Teams → Chat → ··· → Export) and upload here.
            </p>
            <div
              className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center cursor-pointer hover:border-brand hover:bg-blue-50 transition-colors"
              onClick={() => chatRef.current?.click()}
            >
              <MessageSquare size={32} className="mx-auto text-gray-300 mb-2" />
              <p className="text-sm text-gray-500">Click to select the JSON export file</p>
              <input ref={chatRef} type="file" accept=".json" className="hidden"
                onChange={(e) => e.target.files?.[0] && uploadFile(e.target.files[0], "teams-chat")} />
            </div>
          </div>
        )}

        {loading && (
          <div className="flex items-center gap-2 mt-4 text-sm text-gray-500">
            <Loader2 size={14} className="animate-spin" /> Processing...
          </div>
        )}
      </div>

      {/* Recent jobs */}
      {jobs.length > 0 && (
        <div className="mt-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-2">Recent Jobs</h2>
          <div className="space-y-2">
            {jobs.map((j) => (
              <div key={j.job_id} className="bg-white border border-gray-200 rounded-lg px-4 py-2 flex items-center justify-between text-sm">
                <span className="text-gray-700 truncate max-w-xs">{j.source}</span>
                <span className={clsx("flex items-center gap-1", j.status === "done" ? "text-green-600" : j.status === "error" ? "text-red-600" : "text-gray-400")}>
                  {j.status === "done" ? <CheckCircle size={12} /> : j.status === "error" ? <AlertCircle size={12} /> : <Loader2 size={12} className="animate-spin" />}
                  {j.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
