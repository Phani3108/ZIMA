"use client";

import { useState, useCallback, useEffect } from "react";
import { Brain, Search, Plus, ChevronDown, ChevronUp, AlertTriangle, Zap, RefreshCw } from "lucide-react";
import { brain, distill } from "@/lib/api";

// ─── Types ─────────────────────────────────────────────────────────────────

interface BrainEntry {
  id: string;
  text: string;
  category: string;
  level: string;
  confidence: number;
  role_weight?: number;
  contributed_by?: string;
  tags: string[];
  score?: number;
  status?: string;
}

// ─── Constants ──────────────────────────────────────────────────────────────

const CATEGORY_COLORS: Record<string, string> = {
  brand_voice:       "bg-blue-100 text-blue-700",
  copy_pattern:      "bg-purple-100 text-purple-700",
  design_guideline:  "bg-pink-100 text-pink-700",
  process:           "bg-green-100 text-green-700",
  client_preference: "bg-orange-100 text-orange-700",
  market_insight:    "bg-teal-100 text-teal-700",
  general:           "bg-gray-100 text-gray-600",
};

const LEVEL_BADGE: Record<string, string> = {
  zeta:     "bg-indigo-100 text-indigo-700",
  team:     "bg-yellow-100 text-yellow-700",
  personal: "bg-emerald-100 text-emerald-700",
};

// ─── Sub-components ─────────────────────────────────────────────────────────

function KnowledgeCard({ entry, onResolve }: {
  entry: BrainEntry;
  onResolve?: (id: string, resolution: "accept" | "reject") => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const isConflict = entry.status === "conflict";

  return (
    <div className={`border rounded-lg p-4 bg-white shadow-sm ${isConflict ? "border-amber-300" : "border-gray-200"}`}>
      <div className="flex items-start gap-3">
        {isConflict && <AlertTriangle size={16} className="text-amber-500 mt-0.5 shrink-0" />}
        <div className="flex-1 min-w-0">
          <p className="text-sm text-gray-800 leading-snug">{entry.text}</p>
          <div className="flex flex-wrap gap-1.5 mt-2">
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${CATEGORY_COLORS[entry.category] || CATEGORY_COLORS.general}`}>
              {entry.category.replace(/_/g, " ")}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${LEVEL_BADGE[entry.level] || LEVEL_BADGE.personal}`}>
              {entry.level}
            </span>
            {entry.tags?.slice(0, 3).map((tag) => (
              <span key={tag} className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">
                #{tag}
              </span>
            ))}
          </div>
        </div>
        <div className="flex flex-col items-end gap-1 shrink-0">
          {entry.score !== undefined && (
            <span className="text-xs text-gray-400">{(entry.score * 100).toFixed(0)}% match</span>
          )}
          <span className="text-xs text-gray-400">{(entry.confidence * 100).toFixed(0)}% confident</span>
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-gray-400 hover:text-gray-600"
          >
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="mt-3 pt-3 border-t border-gray-100 text-xs text-gray-500 space-y-1">
          <p>ID: <code className="bg-gray-50 px-1 rounded">{entry.id}</code></p>
          {entry.contributed_by && <p>By: {entry.contributed_by}</p>}
        </div>
      )}

      {isConflict && onResolve && (
        <div className="flex gap-2 mt-3">
          <button
            onClick={() => onResolve(entry.id, "accept")}
            className="text-xs px-3 py-1 rounded bg-green-600 text-white hover:bg-green-700"
          >
            Accept
          </button>
          <button
            onClick={() => onResolve(entry.id, "reject")}
            className="text-xs px-3 py-1 rounded bg-red-100 text-red-600 hover:bg-red-200"
          >
            Reject
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Main page ───────────────────────────────────────────────────────────────

export default function BrainPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<BrainEntry[]>([]);
  const [conflicts, setConflicts] = useState<BrainEntry[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [category, setCategory] = useState("");
  const [level, setLevel] = useState("");
  const [compactResult, setCompactResult] = useState<{compacted: number; new_brain_entries: number} | null>(null);
  const [isCompacting, setIsCompacting] = useState(false);
  const [contributeText, setContributeText] = useState("");
  const [contributeCategory, setContributeCategory] = useState("general");
  const [isContributing, setIsContributing] = useState(false);
  const [contributeMsg, setContributeMsg] = useState("");

  // Load conflicts on mount
  useEffect(() => {
    brain.conflicts().then(setConflicts).catch(() => {});
  }, []);

  const handleSearch = useCallback(async () => {
    if (!query.trim()) return;
    setIsSearching(true);
    try {
      const data = await brain.query(query, {
        category: category || undefined,
        level: level || undefined,
        top_k: 12,
      });
      setResults(data);
    } catch {
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  }, [query, category, level]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSearch();
  };

  const handleResolve = async (id: string, resolution: "accept" | "reject") => {
    await brain.resolveConflict(id, resolution);
    setConflicts((prev) => prev.filter((c) => c.id !== id));
  };

  const handleContribute = async () => {
    if (!contributeText.trim()) return;
    setIsContributing(true);
    try {
      const result = await brain.contribute({
        text: contributeText,
        category: contributeCategory,
        level: "zeta",
      });
      setContributeMsg(`Saved (${result.action})`);
      setContributeText("");
      setTimeout(() => setContributeMsg(""), 3000);
    } catch {
      setContributeMsg("Failed to save");
    } finally {
      setIsContributing(false);
    }
  };

  const handleCompact = async () => {
    setIsCompacting(true);
    try {
      const result = await brain.compact();
      setCompactResult(result);
    } catch {
      setCompactResult(null);
    } finally {
      setIsCompacting(false);
    }
  };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-6 py-5 border-b border-gray-200 bg-white">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Brain size={20} className="text-indigo-600" />
            <div>
              <h1 className="text-base font-semibold text-gray-900">Agency Brain</h1>
              <p className="text-xs text-gray-500 mt-0.5">Aggregated knowledge from all campaigns and conversations</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {conflicts.length > 0 && (
              <span className="flex items-center gap-1 text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded-full">
                <AlertTriangle size={12} />
                {conflicts.length} conflict{conflicts.length > 1 ? "s" : ""} need review
              </span>
            )}
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="text-xs text-gray-500 hover:text-gray-700 px-2 py-1 border border-gray-200 rounded"
            >
              {showAdvanced ? "Hide" : "Advanced"}
            </button>
          </div>
        </div>

        {/* Search */}
        <div className="mt-4 flex gap-2">
          <div className="relative flex-1">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Search the agency brain..."
              className="w-full pl-9 pr-4 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-400 focus:border-transparent outline-none"
            />
          </div>
          <button
            onClick={handleSearch}
            disabled={isSearching}
            className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
          >
            {isSearching ? "..." : "Search"}
          </button>
        </div>

        {/* Advanced filters */}
        {showAdvanced && (
          <div className="mt-3 flex gap-3 flex-wrap items-center">
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="text-xs border border-gray-200 rounded px-2 py-1.5 bg-white text-gray-600"
            >
              <option value="">All categories</option>
              {Object.keys(CATEGORY_COLORS).filter(k => k !== "general").map(c => (
                <option key={c} value={c}>{c.replace(/_/g, " ")}</option>
              ))}
            </select>
            <select
              value={level}
              onChange={(e) => setLevel(e.target.value)}
              className="text-xs border border-gray-200 rounded px-2 py-1.5 bg-white text-gray-600"
            >
              <option value="">All levels</option>
              <option value="zeta">Zeta (agency-wide)</option>
              <option value="team">Team</option>
              <option value="personal">Personal</option>
            </select>
            <button
              onClick={handleCompact}
              disabled={isCompacting}
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 border border-gray-200 rounded hover:bg-gray-50 text-gray-600"
            >
              <RefreshCw size={12} className={isCompacting ? "animate-spin" : ""} />
              Sprint Compact
            </button>
            {compactResult && (
              <span className="text-xs text-green-600">
                Compacted {compactResult.compacted} → {compactResult.new_brain_entries} rules
              </span>
            )}
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Conflicts section */}
        {conflicts.length > 0 && (
          <div>
            <h2 className="flex items-center gap-2 text-sm font-medium text-amber-700 mb-3">
              <AlertTriangle size={14} />
              Conflicts Needing Review
            </h2>
            <div className="space-y-2">
              {conflicts.map((c) => (
                <KnowledgeCard key={c.id} entry={c} onResolve={handleResolve} />
              ))}
            </div>
          </div>
        )}

        {/* Search results */}
        {results.length > 0 && (
          <div>
            <h2 className="text-sm font-medium text-gray-700 mb-3">
              {results.length} result{results.length > 1 ? "s" : ""}
            </h2>
            <div className="space-y-2">
              {results.map((r) => (
                <KnowledgeCard key={r.id} entry={r} />
              ))}
            </div>
          </div>
        )}

        {results.length === 0 && !isSearching && (
          <div className="text-center py-16 text-gray-400">
            <Brain size={40} className="mx-auto mb-3 opacity-20" />
            <p className="text-sm">Search the agency brain above</p>
            <p className="text-xs mt-1">The brain accumulates knowledge from every approved campaign</p>
          </div>
        )}

        {/* Contribute panel */}
        {showAdvanced && (
          <div className="border border-dashed border-gray-300 rounded-lg p-4 bg-gray-50">
            <h2 className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-3">
              <Plus size={14} />
              Contribute Knowledge
            </h2>
            <textarea
              value={contributeText}
              onChange={(e) => setContributeText(e.target.value)}
              placeholder="Share a marketing insight, brand rule, or process improvement..."
              rows={3}
              className="w-full text-sm border border-gray-200 rounded-lg p-3 focus:ring-2 focus:ring-indigo-400 outline-none resize-none"
            />
            <div className="flex items-center gap-2 mt-2">
              <select
                value={contributeCategory}
                onChange={(e) => setContributeCategory(e.target.value)}
                className="text-xs border border-gray-200 rounded px-2 py-1.5 bg-white"
              >
                {Object.keys(CATEGORY_COLORS).map(c => (
                  <option key={c} value={c}>{c.replace(/_/g, " ")}</option>
                ))}
              </select>
              <button
                onClick={handleContribute}
                disabled={isContributing || !contributeText.trim()}
                className="text-xs px-3 py-1.5 bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
              >
                {isContributing ? "Saving..." : "Contribute"}
              </button>
              {contributeMsg && (
                <span className="text-xs text-green-600">{contributeMsg}</span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
