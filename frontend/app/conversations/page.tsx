"use client";

import { useState, useEffect } from "react";
import {
  MessageCircle, Search, Clock, User, Tag, ChevronRight,
  CheckCircle2, XCircle, Loader2, Filter, Calendar,
  Bot, Sparkles,
} from "lucide-react";
import clsx from "clsx";
import { history } from "@/lib/api";
import { useBackend } from "@/lib/useBackend";
import OfflineBanner from "@/components/OfflineBanner";

type Session = {
  id: string;
  team_id: string;
  user_id: string;
  brief: string;
  pipeline_id: string;
  outcome: string;
  tags: string[];
  created_at: string;
  messages_json?: Array<{ role: string; content: string }>;
};

const STATIC_SESSIONS: Session[] = [
  {
    id: "sess-001", team_id: "demo", user_id: "user-1", brief: "Write a high-converting landing page for our SaaS product launch",
    pipeline_id: "content_pipeline", outcome: "approved", tags: ["landing-page", "conversion"],
    created_at: "2025-01-18T14:30:00Z",
    messages_json: [
      { role: "user", content: "I need a landing page for our new SaaS product." },
      { role: "assistant", content: "I'll create a high-converting landing page. Let me gather brand voice and competitor data..." },
    ],
  },
  {
    id: "sess-002", team_id: "demo", user_id: "user-1", brief: "Create a 5-email nurture sequence for trial users",
    pipeline_id: "email_pipeline", outcome: "approved", tags: ["email", "nurture", "onboarding"],
    created_at: "2025-01-17T10:15:00Z",
    messages_json: [
      { role: "user", content: "We need an email nurture sequence for new trial users." },
      { role: "assistant", content: "I'll design a 5-email sequence targeting trial-to-paid conversion..." },
    ],
  },
  {
    id: "sess-003", team_id: "demo", user_id: "user-2", brief: "Analyze competitor SEO strategy and identify content gaps",
    pipeline_id: "seo_pipeline", outcome: "approved", tags: ["seo", "competitive", "research"],
    created_at: "2025-01-16T09:00:00Z",
    messages_json: [
      { role: "user", content: "What are our top 3 competitors doing in SEO that we're not?" },
      { role: "assistant", content: "Running competitive analysis across SEMRush data..." },
    ],
  },
  {
    id: "sess-004", team_id: "demo", user_id: "user-1", brief: "Design social media campaign for Black Friday",
    pipeline_id: "social_pipeline", outcome: "rejected", tags: ["social", "campaign", "seasonal"],
    created_at: "2025-01-15T16:45:00Z",
    messages_json: [
      { role: "user", content: "Plan a social media blitz for Black Friday." },
      { role: "assistant", content: "I'll create a multi-platform campaign spanning Instagram, LinkedIn, and Twitter..." },
    ],
  },
  {
    id: "sess-005", team_id: "demo", user_id: "user-3", brief: "Generate product marketing brief for enterprise features",
    pipeline_id: "product_marketing_pipeline", outcome: "approved", tags: ["product-marketing", "enterprise"],
    created_at: "2025-01-14T11:30:00Z",
  },
  {
    id: "sess-006", team_id: "demo", user_id: "user-2", brief: "Create brand voice documentation for new market segment",
    pipeline_id: "brand_pipeline", outcome: "approved", tags: ["brand", "guidelines", "new-market"],
    created_at: "2025-01-13T08:00:00Z",
  },
];

export default function ConversationsPage() {
  const { online, checking } = useBackend();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [outcomeFilter, setOutcomeFilter] = useState<string | null>(null);
  const [selectedSession, setSelectedSession] = useState<Session | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    if (!online) {
      setSessions(STATIC_SESSIONS);
      setLoading(false);
      return;
    }
    setLoading(true);
    history
      .list("demo", "", 50)
      .then((data: any) => setSessions(data.sessions || []))
      .catch(() => setSessions(STATIC_SESSIONS))
      .finally(() => setLoading(false));
  }, [online]);

  const filtered = sessions.filter((s) => {
    if (outcomeFilter && s.outcome !== outcomeFilter) return false;
    if (search && !s.brief.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const handleSelectSession = async (session: Session) => {
    setSelectedSession(session);
    if (online && !session.messages_json) {
      setDetailLoading(true);
      try {
        const detail = await history.detail(session.id, session.team_id);
        setSelectedSession({ ...session, ...detail });
      } catch {
        // keep local data
      }
      setDetailLoading(false);
    }
  };

  const outcomes = Array.from(new Set(sessions.map((s) => s.outcome)));

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <MessageCircle size={24} /> Conversation History
        </h1>
        <p className="text-gray-500 mt-1 text-sm">
          Browse past agent conversations, search by brief, and review outcomes.
        </p>
      </div>

      {!online && !checking && (
        <div className="mb-4 flex items-center gap-2 bg-amber-50 border border-amber-200 text-amber-700 px-4 py-2 rounded-lg text-sm">
          <MessageCircle size={14} /> Showing demo sessions — deploy backend for live data.
        </div>
      )}

      {/* Search & Filter */}
      <div className="flex gap-3 mb-6">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search conversations..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setOutcomeFilter(null)}
            className={clsx(
              "px-3 py-2 rounded-xl text-xs font-medium transition-colors",
              !outcomeFilter ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            )}
          >
            All
          </button>
          {outcomes.map((o) => (
            <button
              key={o}
              onClick={() => setOutcomeFilter(o === outcomeFilter ? null : o)}
              className={clsx(
                "px-3 py-2 rounded-xl text-xs font-medium transition-colors flex items-center gap-1",
                o === outcomeFilter
                  ? o === "approved" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              )}
            >
              {o === "approved" ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
              {o.charAt(0).toUpperCase() + o.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="text-center py-16"><Loader2 size={24} className="animate-spin mx-auto text-gray-400" /></div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Session List */}
          <div className="lg:col-span-2 space-y-2 max-h-[70vh] overflow-y-auto">
            {filtered.length === 0 ? (
              <p className="text-center py-8 text-gray-400 text-sm">No conversations found.</p>
            ) : (
              filtered.map((s) => (
                <button
                  key={s.id}
                  onClick={() => handleSelectSession(s)}
                  className={clsx(
                    "w-full text-left border rounded-xl p-4 transition-all",
                    selectedSession?.id === s.id
                      ? "border-blue-400 bg-blue-50 shadow-sm"
                      : "hover:border-gray-300 hover:bg-gray-50 bg-white"
                  )}
                >
                  <div className="flex items-start justify-between mb-2">
                    <p className="text-sm font-medium text-gray-900 line-clamp-2 flex-1">{s.brief}</p>
                    {s.outcome === "approved" ? (
                      <CheckCircle2 size={16} className="text-green-500 flex-shrink-0 ml-2" />
                    ) : (
                      <XCircle size={16} className="text-red-400 flex-shrink-0 ml-2" />
                    )}
                  </div>
                  <div className="flex items-center gap-3 text-xs text-gray-400">
                    <span className="flex items-center gap-1">
                      <User size={11} /> {s.user_id}
                    </span>
                    <span className="flex items-center gap-1">
                      <Calendar size={11} /> {new Date(s.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  {s.tags?.length > 0 && (
                    <div className="flex gap-1 mt-2">
                      {s.tags.slice(0, 3).map((t) => (
                        <span key={t} className="text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                </button>
              ))
            )}
          </div>

          {/* Detail Panel */}
          <div className="lg:col-span-3">
            {!selectedSession ? (
              <div className="border rounded-2xl bg-white p-8 text-center text-gray-400">
                <MessageCircle size={32} className="mx-auto mb-3 opacity-50" />
                <p className="text-sm">Select a conversation to view details</p>
              </div>
            ) : (
              <div className="border rounded-2xl bg-white overflow-hidden">
                {/* Header */}
                <div className="p-5 border-b">
                  <h2 className="font-semibold text-gray-900 mb-2">{selectedSession.brief}</h2>
                  <div className="flex items-center gap-3 text-sm text-gray-500">
                    <span className={clsx(
                      "px-2 py-0.5 rounded-full text-xs font-medium",
                      selectedSession.outcome === "approved"
                        ? "bg-green-100 text-green-700"
                        : "bg-red-100 text-red-700"
                    )}>
                      {selectedSession.outcome}
                    </span>
                    <span className="flex items-center gap-1"><User size={12} /> {selectedSession.user_id}</span>
                    <span className="flex items-center gap-1"><Clock size={12} /> {new Date(selectedSession.created_at).toLocaleString()}</span>
                    <span className="text-xs bg-gray-100 px-2 py-0.5 rounded">{selectedSession.pipeline_id}</span>
                  </div>
                  {selectedSession.tags?.length > 0 && (
                    <div className="flex gap-1.5 mt-2">
                      {selectedSession.tags.map((t) => (
                        <span key={t} className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full flex items-center gap-1">
                          <Tag size={10} /> {t}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Messages */}
                <div className="p-5 space-y-4 max-h-[50vh] overflow-y-auto">
                  {detailLoading ? (
                    <div className="text-center py-8"><Loader2 size={20} className="animate-spin mx-auto text-gray-400" /></div>
                  ) : selectedSession.messages_json?.length ? (
                    selectedSession.messages_json.map((msg, i) => (
                      <div key={i} className={clsx(
                        "flex gap-3",
                        msg.role === "user" ? "" : ""
                      )}>
                        <div className={clsx(
                          "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0",
                          msg.role === "user" ? "bg-blue-100 text-blue-600" : "bg-purple-100 text-purple-600"
                        )}>
                          {msg.role === "user" ? <User size={14} /> : <Bot size={14} />}
                        </div>
                        <div className={clsx(
                          "flex-1 rounded-xl p-4 text-sm",
                          msg.role === "user" ? "bg-blue-50" : "bg-gray-50"
                        )}>
                          <p className="text-xs font-medium text-gray-500 mb-1">
                            {msg.role === "user" ? "You" : "Agent"}
                          </p>
                          <p className="text-gray-800 whitespace-pre-wrap">{msg.content}</p>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-center py-8 text-gray-400 text-sm">
                      <Sparkles size={24} className="mx-auto mb-2 opacity-50" />
                      Full conversation messages are stored in blob storage. Deploy the backend to retrieve them.
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
