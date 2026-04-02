"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Archive, Plus, Search, Tag, FileText, Code, Globe,
  Clock, User, Share2, MessageSquare, ChevronRight,
  Loader2,
} from "lucide-react";
import clsx from "clsx";
import { artifacts } from "@/lib/api";
import { useBackend } from "@/lib/useBackend";
import OfflineBanner from "@/components/OfflineBanner";

type Artifact = {
  id: string;
  team_id: string;
  title: string;
  content_type: string;
  version: number;
  tags: string[];
  created_by: string;
  created_at: string;
  updated_at: string;
  source_workflow_id?: string;
  skill_id?: string;
};

const TYPE_ICONS: Record<string, any> = {
  markdown: FileText,
  html: Globe,
  text: FileText,
  json: Code,
};

const STATIC_ARTIFACTS: Artifact[] = [
  { id: "art-demo-1", team_id: "demo", title: "Q3 Product Launch Blog Post", content_type: "markdown", version: 3, tags: ["blog", "product-launch"], created_by: "content-strategist", created_at: "2025-01-15T10:30:00Z", updated_at: "2025-01-18T14:20:00Z", skill_id: "blog_writer" },
  { id: "art-demo-2", team_id: "demo", title: "SEO Keyword Research Brief", content_type: "markdown", version: 1, tags: ["seo", "research"], created_by: "seo-agent", created_at: "2025-01-16T09:00:00Z", updated_at: "2025-01-16T09:00:00Z", skill_id: "seo_researcher" },
  { id: "art-demo-3", team_id: "demo", title: "Email Campaign — Winter Sale", content_type: "html", version: 2, tags: ["email", "campaign"], created_by: "email-marketer", created_at: "2025-01-14T16:00:00Z", updated_at: "2025-01-17T11:30:00Z", source_workflow_id: "wf-456" },
  { id: "art-demo-4", team_id: "demo", title: "Social Media Content Calendar", content_type: "json", version: 1, tags: ["social", "planning"], created_by: "social-manager", created_at: "2025-01-17T08:45:00Z", updated_at: "2025-01-17T08:45:00Z" },
  { id: "art-demo-5", team_id: "demo", title: "Brand Voice Guidelines v2", content_type: "markdown", version: 2, tags: ["brand", "guidelines"], created_by: "brand-strategist", created_at: "2025-01-10T13:00:00Z", updated_at: "2025-01-18T10:00:00Z" },
  { id: "art-demo-6", team_id: "demo", title: "Competitive Analysis Report", content_type: "markdown", version: 1, tags: ["research", "competitive"], created_by: "market-analyst", created_at: "2025-01-18T07:30:00Z", updated_at: "2025-01-18T07:30:00Z", skill_id: "competitive_intel" },
];

export default function ArtifactsPage() {
  const { online, checking } = useBackend();
  const [items, setItems] = useState<Artifact[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedTag, setSelectedTag] = useState<string | null>(null);

  useEffect(() => {
    if (!online) {
      setItems(STATIC_ARTIFACTS);
      setLoading(false);
      return;
    }
    setLoading(true);
    artifacts
      .list("demo", search, selectedTag || "")
      .then((data: any) => setItems(data.artifacts || []))
      .catch(() => setItems(STATIC_ARTIFACTS))
      .finally(() => setLoading(false));
  }, [online, search, selectedTag]);

  const allTags = Array.from(new Set(items.flatMap((a) => a.tags)));
  const filtered = items.filter((a) => {
    if (selectedTag && !a.tags.includes(selectedTag)) return false;
    if (search && !a.title.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Archive size={24} /> Artifact Library
          </h1>
          <p className="text-gray-500 mt-1 text-sm">
            Versioned approved outputs with shareable links and external review.
          </p>
        </div>
        {online && (
          <button className="flex items-center gap-2 bg-brand hover:bg-blue-700 text-white px-4 py-2 rounded-xl text-sm font-medium transition-colors">
            <Plus size={14} /> Save Artifact
          </button>
        )}
      </div>

      {!online && !checking && (
        <div className="mb-4 flex items-center gap-2 bg-amber-50 border border-amber-200 text-amber-700 px-4 py-2 rounded-lg text-sm">
          <Archive size={14} /> Showing demo artifacts — deploy backend for live data.
        </div>
      )}

      {/* Search & Filter Bar */}
      <div className="flex gap-3 mb-6">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search artifacts..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
      </div>

      {/* Tag chips */}
      {allTags.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-6">
          <button
            onClick={() => setSelectedTag(null)}
            className={clsx(
              "px-3 py-1 rounded-full text-xs font-medium transition-colors",
              !selectedTag ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            )}
          >
            All
          </button>
          {allTags.map((tag) => (
            <button
              key={tag}
              onClick={() => setSelectedTag(tag === selectedTag ? null : tag)}
              className={clsx(
                "px-3 py-1 rounded-full text-xs font-medium transition-colors flex items-center gap-1",
                tag === selectedTag ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              )}
            >
              <Tag size={10} /> {tag}
            </button>
          ))}
        </div>
      )}

      {/* Grid */}
      {loading ? (
        <div className="text-center py-16">
          <Loader2 size={24} className="animate-spin mx-auto text-gray-400" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 text-gray-400">No artifacts found.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((a) => {
            const Icon = TYPE_ICONS[a.content_type] || FileText;
            return (
              <Link
                key={a.id}
                href={`/artifacts/${a.id}`}
                className="group border rounded-2xl p-5 hover:shadow-md hover:border-blue-200 transition-all bg-white"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-lg bg-blue-50 text-blue-600">
                      <Icon size={18} />
                    </div>
                    <span className="text-xs font-medium text-gray-400 uppercase">
                      {a.content_type}
                    </span>
                  </div>
                  <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">
                    v{a.version}
                  </span>
                </div>
                <h3 className="font-semibold text-gray-900 group-hover:text-blue-600 transition-colors mb-2 line-clamp-2">
                  {a.title}
                </h3>
                <div className="flex flex-wrap gap-1 mb-3">
                  {a.tags.slice(0, 3).map((t) => (
                    <span key={t} className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">
                      {t}
                    </span>
                  ))}
                </div>
                <div className="flex items-center justify-between text-xs text-gray-400">
                  <span className="flex items-center gap-1">
                    <User size={12} /> {a.created_by}
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock size={12} /> {new Date(a.updated_at).toLocaleDateString()}
                  </span>
                </div>
                {a.source_workflow_id && (
                  <div className="mt-2 text-xs text-blue-500 flex items-center gap-1">
                    <Share2 size={10} /> From workflow
                  </div>
                )}
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
