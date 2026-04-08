"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Loader2, CheckCircle, XCircle, Bot, User, ListChecks, MessageSquare, Sparkles, GitBranch } from "lucide-react";
import clsx from "clsx";
import { useBackend } from "@/lib/useBackend";
import DemoBanner from "@/components/DemoBanner";
import ExecutionCard from "@/components/future/ExecutionCard";
import JobHistoryPanel from "@/components/future/JobHistoryPanel";
import { futureTemplates } from "@/lib/api";

type AgentStep = {
  from: string;
  step_name: string;
  step_index: number;
  total_steps: number;
  status: "started" | "completed";
  preview?: string;
};

type PipelineStep = {
  name: string;
  agent: string;
  description: string;
  is_human_gate: boolean;
};

type Suggestion = {
  id: string;
  brief: string;
  output_text: string;
  review_scores: Record<string, number>;
  created_at: string;
  status: string;
};

type Message =
  | { role: "user"; content: string }
  | { role: "assistant"; content: string; type?: string }
  | { role: "draft"; draft: string; review: Record<string, unknown>; iteration: number; brief: string; approver?: string };

type Template = { id: string; name: string; icon: string; description: string };

const API_WS = process.env.NEXT_PUBLIC_API_URL?.replace("http", "ws") || "ws://localhost:8000";

/* ─── Demo Data ─────────────────────────────────────────────────── */

const DEMO_TEMPLATES = [
  { id: "linkedin_post", name: "LinkedIn Post", icon: "💼", description: "Professional LinkedIn content" },
  { id: "blog_post", name: "Blog Post", icon: "📝", description: "Long-form SEO blog article" },
  { id: "campaign_copy", name: "Campaign Copy", icon: "📣", description: "Full campaign with visuals" },
  { id: "seo_article", name: "SEO Article", icon: "🔍", description: "Search-optimized content" },
  { id: "email_sequence", name: "Email Sequence", icon: "📧", description: "Multi-touch email flow" },
  { id: "ad_copy", name: "Ad Copy", icon: "🎯", description: "Paid ad creative" },
];

const DEMO_PIPELINE = [
  { name: "Research", agent: "research", description: "Search knowledge base", is_human_gate: false },
  { name: "Draft Copy", agent: "copy", description: "Generate content", is_human_gate: false },
  { name: "Quality Review", agent: "review", description: "Score against rubric", is_human_gate: false },
  { name: "Manager Approval", agent: "approval", description: "Route to team lead", is_human_gate: true },
  { name: "SEO Optimize", agent: "seo", description: "Keyword optimization", is_human_gate: false },
];

const DEMO_STEPS: Record<string, AgentStep[]> = {
  research: [
    { from: "research", step_name: "Searching knowledge base", step_index: 0, total_steps: 3, status: "completed" },
    { from: "research", step_name: "Searching agency brain", step_index: 1, total_steps: 3, status: "completed" },
    { from: "research", step_name: "Research complete", step_index: 2, total_steps: 3, status: "completed" },
  ],
  copy: [
    { from: "copy", step_name: "Loading brand context", step_index: 0, total_steps: 5, status: "completed" },
    { from: "copy", step_name: "Fetching learning guidance", step_index: 1, total_steps: 5, status: "completed" },
    { from: "copy", step_name: "Reading PM handoff", step_index: 2, total_steps: 5, status: "completed" },
    { from: "copy", step_name: "Generating draft", step_index: 3, total_steps: 5, status: "completed", preview: "🚀 Exciting news! We've raised..." },
    { from: "copy", step_name: "Draft complete", step_index: 4, total_steps: 5, status: "completed" },
  ],
  review: [
    { from: "review", step_name: "Running reflection loop", step_index: 0, total_steps: 4, status: "completed" },
    { from: "review", step_name: "Scoring against rubric", step_index: 1, total_steps: 4, status: "completed" },
    { from: "review", step_name: "Checking auto-approval", step_index: 2, total_steps: 4, status: "started" },
  ],
};

const DEMO_SUGGESTIONS: Suggestion[] = [
  {
    id: "demo-1",
    brief: "LinkedIn post about Q2 product launch",
    output_text: "🚀 Big news from the team! After months of development, we're thrilled to announce the launch of our AI-powered campaign builder...",
    review_scores: { brand_fit: 9, clarity: 8, cta_strength: 7 },
    created_at: "2026-04-06T14:30:00Z",
    status: "approved",
  },
  {
    id: "demo-2",
    brief: "Series A funding announcement post",
    output_text: "We're excited to share that we've raised $12M in Series A funding led by Acme Ventures. This milestone fuels our mission...",
    review_scores: { brand_fit: 9, clarity: 9, cta_strength: 8 },
    created_at: "2026-04-04T09:15:00Z",
    status: "approved",
  },
];

const DEMO_MESSAGES: Message[] = [
  { role: "user", content: "Write a LinkedIn post about our Series A funding of $12M" },
  { role: "assistant", content: "Analysing brief and pulling brand context...", type: "thinking" },
  {
    role: "draft",
    draft: "🚀 Exciting news! We've raised $12M in Series A funding led by Acme Ventures.\n\nThis milestone means we can double down on our mission: making AI-powered marketing accessible to every team.\n\nWhat's next:\n→ Expanding our agent platform\n→ Hiring across engineering & GTM\n→ Launching 3 new integrations\n\nThank you to our customers, team, and investors who believe in the future of autonomous marketing.\n\n#SeriesA #MarTech #AI",
    review: { brand_fit: 9, clarity: 8, cta_strength: 7, tone: 8 },
    iteration: 1,
    brief: "Write a LinkedIn post about our Series A funding of $12M",
    approver: "Mithun",
  },
];

/* ─── Component ─────────────────────────────────────────────────── */

export default function FutureChatPage() {
  const { online, checking } = useBackend();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [comment, setComment] = useState("");
  const [sessionId] = useState(() =>
    typeof crypto !== "undefined" ? crypto.randomUUID() : Math.random().toString(36).slice(2)
  );

  // Template picker
  const [templates, setTemplates] = useState<Template[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);

  // Execution visibility
  const [agentSteps, setAgentSteps] = useState<Record<string, AgentStep[]>>({});
  const [pipelineSteps, setPipelineSteps] = useState<PipelineStep[]>([]);
  const [activeAgent, setActiveAgent] = useState<string | null>(null);

  // Job suggestions
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [priorJobId, setPriorJobId] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Load templates on mount
  useEffect(() => {
    futureTemplates.list().then(setTemplates).catch(() => {});
  }, []);

  // Scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, agentSteps]);

  // WebSocket connection
  useEffect(() => {
    if (!online) return;
    const ws = new WebSocket(`${API_WS}/ws/future/chat/${sessionId}`);
    wsRef.current = ws;

    ws.onmessage = (ev) => {
      const data = JSON.parse(ev.data);

      if (data.type === "pipeline_plan") {
        setPipelineSteps(data.steps || []);
      } else if (data.type === "job_suggestions") {
        setSuggestions(data.suggestions || []);
        setShowSuggestions(true);
      } else if (data.type === "agent_step") {
        setActiveAgent(data.from);
        setAgentSteps((prev) => {
          const key = data.from;
          const existing = prev[key] || [];
          const idx = existing.findIndex(
            (s) => s.step_index === data.step_index && s.step_name === data.step_name
          );
          const updated = [...existing];
          if (idx >= 0) {
            updated[idx] = data;
          } else {
            updated.push(data);
          }
          return { ...prev, [key]: updated };
        });
      } else if (data.type === "thinking") {
        setLoading(true);
        setMessages((m) => [...m, { role: "assistant", content: data.text, type: "thinking" }]);
      } else if (data.type === "awaiting_approval") {
        setLoading(false);
        setMessages((m) => [
          ...m,
          {
            role: "draft",
            draft: data.draft,
            review: data.review,
            iteration: data.iteration,
            brief: data.brief,
            approver: data.approver,
          },
        ]);
      } else if (data.type === "done") {
        setLoading(false);
        setActiveAgent(null);
        setMessages((m) => [
          ...m,
          { role: "assistant", content: "Approved and saved to brand memory.", type: "done" },
        ]);
      } else if (data.type === "error") {
        setLoading(false);
        setMessages((m) => [...m, { role: "assistant", content: `Error: ${data.text}`, type: "error" }]);
      } else if (data.type === "status") {
        setMessages((m) => [...m, { role: "assistant", content: data.text, type: "status" }]);
      }
    };

    return () => ws.close();
  }, [online, sessionId]);

  const send = useCallback(() => {
    if (!input.trim() || !wsRef.current) return;
    const brief = input.trim();
    setMessages((m) => [...m, { role: "user", content: brief }]);
    setInput("");
    setLoading(true);
    setAgentSteps({});
    setPipelineSteps([]);

    wsRef.current.send(
      JSON.stringify({
        type: "message",
        brief,
        task_template_id: selectedTemplate,
        prior_job_id: priorJobId,
      })
    );
    setPriorJobId(null);
  }, [input, selectedTemplate, priorJobId]);

  const decide = useCallback(
    (decision: "approve" | "reject") => {
      if (!wsRef.current) return;
      wsRef.current.send(JSON.stringify({ type: decision, comment }));
      setComment("");
      setLoading(true);
    },
    [comment]
  );

  if (checking)
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="animate-spin text-gray-400" size={24} />
      </div>
    );

  /* ── Use demo data when backend is offline ── */
  const showDemo = !online;
  const displayTemplates = showDemo ? DEMO_TEMPLATES : templates;
  const displayMessages = showDemo ? DEMO_MESSAGES : messages;
  const displayPipeline = showDemo ? DEMO_PIPELINE : pipelineSteps;
  const displaySteps = showDemo ? DEMO_STEPS : agentSteps;
  const displaySuggestions = showDemo ? DEMO_SUGGESTIONS : suggestions;
  const displayActiveAgent = showDemo ? "review" : activeAgent;

  return (
    <div className="flex h-full">
      {/* Main Chat */}
      <div className="flex-1 flex flex-col max-w-3xl mx-auto px-4 py-6">
        <h1 className="text-xl font-semibold text-gray-800 mb-1 flex items-center gap-2">
          <ListChecks className="w-5 h-5" />
          Future Chat
        </h1>
        <p className="text-sm text-gray-500 mb-4">
          Chat with AI agents and watch every step of the content pipeline in real time.
        </p>

        {showDemo && (
          <DemoBanner
            feature="Future Chat"
            steps={[
              "Start the backend — docker compose up (Redis, Qdrant, PostgreSQL)",
              "Pick a task template like \"LinkedIn Post\" and type a brief",
              "Watch agents work step-by-step, then approve or reject the draft",
            ]}
          />
        )}

        {/* Stats row */}
        {showDemo && (
          <div className="grid grid-cols-3 gap-3 mb-4">
            <div className="bg-white border rounded-xl p-3">
              <div className="flex items-center gap-1.5 mb-1">
                <MessageSquare size={13} className="text-gray-400" />
                <span className="text-[11px] text-gray-500 uppercase tracking-wider">Templates</span>
              </div>
              <div className="text-xl font-bold text-blue-600">7</div>
            </div>
            <div className="bg-white border rounded-xl p-3">
              <div className="flex items-center gap-1.5 mb-1">
                <GitBranch size={13} className="text-gray-400" />
                <span className="text-[11px] text-gray-500 uppercase tracking-wider">Pipeline Steps</span>
              </div>
              <div className="text-xl font-bold text-purple-600">5</div>
            </div>
            <div className="bg-white border rounded-xl p-3">
              <div className="flex items-center gap-1.5 mb-1">
                <Sparkles size={13} className="text-gray-400" />
                <span className="text-[11px] text-gray-500 uppercase tracking-wider">Suggestions</span>
              </div>
              <div className="text-xl font-bold text-amber-600">2</div>
            </div>
          </div>
        )}

        {/* Template Picker */}
        {displayTemplates.length > 0 && (
          <div className="flex gap-2 flex-wrap mb-4">
            {displayTemplates.map((t) => (
              <button
                key={t.id}
                onClick={() =>
                  showDemo ? null : setSelectedTemplate((prev) => (prev === t.id ? null : t.id))
                }
                className={clsx(
                  "text-xs px-3 py-1.5 rounded-full border transition-colors",
                  (showDemo && t.id === "linkedin_post") || selectedTemplate === t.id
                    ? "bg-blue-600 text-white border-blue-600"
                    : "bg-white text-gray-600 border-gray-200 hover:border-blue-300"
                )}
              >
                {t.icon} {t.name}
              </button>
            ))}
          </div>
        )}

        {/* Job Suggestions */}
        {showSuggestions && displaySuggestions.length > 0 && (
          <JobHistoryPanel
            suggestions={displaySuggestions}
            onUse={(id) => {
              if (showDemo) return;
              setPriorJobId(id);
              setShowSuggestions(false);
            }}
            onEdit={(id) => {
              if (showDemo) return;
              setPriorJobId(id);
              setShowSuggestions(false);
            }}
            onDismiss={() => showDemo ? null : setShowSuggestions(false)}
          />
        )}

        {/* Pipeline Progress Banner */}
        {displayPipeline.length > 0 && (
          <div className="bg-gray-50 border rounded-lg p-3 mb-4">
            <div className="text-xs font-medium text-gray-500 mb-2 uppercase tracking-wide">
              Pipeline
            </div>
            <div className="flex gap-1 items-center flex-wrap">
              {displayPipeline.map((step, i) => {
                const stepDone = displaySteps[step.agent]?.some(
                  (s) => s.status === "completed"
                );
                return (
                  <div key={i} className="flex items-center gap-1">
                    {i > 0 && <span className="text-gray-300 text-xs">→</span>}
                    <span
                      className={clsx(
                        "text-xs px-2 py-0.5 rounded-full",
                        stepDone
                          ? "bg-green-100 text-green-700"
                          : displayActiveAgent === step.agent
                          ? "bg-blue-100 text-blue-700 font-medium"
                          : "bg-gray-100 text-gray-500"
                      )}
                    >
                      {step.name}
                      {step.is_human_gate && " 🔒"}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 space-y-3 overflow-y-auto pb-4">
          {displayMessages.map((msg, i) => {
            if (msg.role === "user") {
              return (
                <div key={i} className="flex justify-end">
                  <div className="bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-2 max-w-lg text-sm">
                    {msg.content}
                  </div>
                </div>
              );
            }
            if (msg.role === "draft") {
              return (
                <div key={i} className="bg-white border rounded-xl p-4 shadow-sm space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-gray-800">
                      Draft #{msg.iteration}
                    </span>
                    {msg.approver && (
                      <span className="text-xs text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full">
                        Needs {msg.approver}&apos;s approval
                      </span>
                    )}
                  </div>
                  <p className="text-gray-700 text-sm whitespace-pre-wrap">{msg.draft}</p>
                  {msg.review && Object.keys(msg.review).length > 0 && (
                    <div className="flex gap-2 flex-wrap">
                      {Object.entries(msg.review).map(([k, v]) => (
                        <span key={k} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                          {k}: {String(v)}
                        </span>
                      ))}
                    </div>
                  )}
                  <div className="flex gap-2 pt-2 border-t">
                    <input
                      value={comment}
                      onChange={(e) => setComment(e.target.value)}
                      placeholder="Optional feedback..."
                      className="flex-1 text-sm border rounded px-2 py-1"
                      disabled={showDemo}
                    />
                    <button
                      onClick={() => decide("approve")}
                      disabled={showDemo}
                      className="flex items-center gap-1 px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700 disabled:opacity-50"
                    >
                      <CheckCircle className="w-4 h-4" /> Approve
                    </button>
                    <button
                      onClick={() => decide("reject")}
                      disabled={showDemo}
                      className="flex items-center gap-1 px-3 py-1 bg-red-500 text-white text-sm rounded hover:bg-red-600 disabled:opacity-50"
                    >
                      <XCircle className="w-4 h-4" /> Reject
                    </button>
                  </div>
                </div>
              );
            }
            return (
              <div key={i} className="flex justify-start">
                <div
                  className={clsx(
                    "rounded-2xl rounded-tl-sm px-4 py-2 max-w-lg text-sm",
                    msg.type === "error"
                      ? "bg-red-50 text-red-700"
                      : msg.type === "done"
                      ? "bg-green-50 text-green-700"
                      : msg.type === "thinking"
                      ? "bg-gray-100 text-gray-500 italic"
                      : "bg-gray-100 text-gray-700"
                  )}
                >
                  {msg.content}
                </div>
              </div>
            );
          })}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="flex gap-2 pt-2 border-t">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
            placeholder={
              selectedTemplate
                ? `Describe your ${selectedTemplate.replace("_", " ")}...`
                : "Type a marketing brief..."
            }
            className="flex-1 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading || showDemo}
          />
          <button
            onClick={send}
            disabled={loading || !input.trim() || showDemo}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Execution Sidebar */}
      {Object.keys(displaySteps).length > 0 && (
        <div className="w-72 border-l bg-gray-50 p-3 overflow-y-auto hidden lg:block">
          <div className="text-xs font-medium text-gray-500 mb-3 uppercase tracking-wide">
            Agent Activity
          </div>
          {Object.entries(displaySteps).map(([agent, steps]) => (
            <ExecutionCard
              key={agent}
              agentName={agent}
              steps={steps}
              isActive={displayActiveAgent === agent}
            />
          ))}
        </div>
      )}
    </div>
  );
}
