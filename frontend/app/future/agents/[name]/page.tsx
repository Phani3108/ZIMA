"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Briefcase, BookOpen, Users, MessageSquare, History } from "lucide-react";
import clsx from "clsx";
import { useBackend } from "@/lib/useBackend";
import DemoBanner from "@/components/DemoBanner";
import { futureAgents } from "@/lib/api";

type Agent = {
  id: string;
  title: string;
  department: string;
  node_name: string;
  responsibilities: string[];
  expertise: string[];
  reports_to: string;
  interacts_with: string[];
  persona_prompt: string;
  avatar_emoji: string;
};

type Job = {
  id: string;
  brief: string;
  output_text: string;
  review_scores: Record<string, number>;
  created_at: string;
  status: string;
  task_template_id: string;
};

const TABS = [
  { key: "profile", label: "Profile", icon: BookOpen },
  { key: "jobs", label: "Job History", icon: History },
  { key: "skills", label: "Expertise", icon: Briefcase },
  { key: "connections", label: "Connections", icon: Users },
  { key: "prompt", label: "System Prompt", icon: MessageSquare },
] as const;

type Tab = (typeof TABS)[number]["key"];

/* ─── Demo Data ─────────────────────────────────────────────────── */

const DEMO_AGENTS: Record<string, Agent> = {
  senior_copywriter: {
    id: "senior_copywriter",
    title: "Senior Copywriter",
    department: "content",
    node_name: "copy",
    responsibilities: ["Write on-brand marketing copy for all channels", "Adapt tone per platform (LinkedIn formal, Twitter concise, Email warm)", "Incorporate brand voice guidelines from memory", "Iterate on drafts based on reviewer feedback"],
    expertise: ["LinkedIn posts", "Blog articles", "Email sequences", "Ad copy", "Brand voice adaptation", "CTA optimization"],
    reports_to: "cmo",
    interacts_with: ["quality_reviewer", "seo_specialist", "project_manager"],
    persona_prompt: "You are the Senior Copywriter at Zeta Marketing Agency. You craft compelling, on-brand copy that drives engagement. You always check brand voice guidelines before drafting and adapt your tone to the target platform. Your copy is concise, punchy, and action-oriented.",
    avatar_emoji: "✍️",
  },
  quality_reviewer: {
    id: "quality_reviewer",
    title: "Quality Reviewer",
    department: "content",
    node_name: "review",
    responsibilities: ["Score every draft against brand rubric (brand_fit, clarity, cta_strength, tone)", "Run reflection loops to improve quality", "Gate content below threshold score", "Provide actionable improvement suggestions"],
    expertise: ["Brand consistency scoring", "Tone analysis", "Quality rubric evaluation", "Content governance"],
    reports_to: "cmo",
    interacts_with: ["senior_copywriter", "cmo"],
    persona_prompt: "You are the Quality Reviewer at Zeta Marketing Agency. Your role is to ensure every piece of content meets brand standards. You score on 4 dimensions: brand_fit, clarity, cta_strength, and tone — each out of 10. Content below 7.0 average is sent back for revision.",
    avatar_emoji: "🔍",
  },
  seo_specialist: {
    id: "seo_specialist",
    title: "SEO Specialist",
    department: "strategy",
    node_name: "seo",
    responsibilities: ["Analyze keywords for target audience", "Optimize content for search rankings", "Generate meta descriptions and title tags", "Suggest internal linking opportunities"],
    expertise: ["Keyword research", "On-page SEO", "Content optimization", "Search intent analysis", "Meta tag generation"],
    reports_to: "cmo",
    interacts_with: ["senior_copywriter", "research_analyst"],
    persona_prompt: "You are the SEO Specialist at Zeta Marketing Agency. You optimize every piece of content for maximum search visibility while maintaining readability and brand voice. You balance keyword density with natural language.",
    avatar_emoji: "📈",
  },
};

const DEMO_JOBS: Job[] = [
  {
    id: "job-1",
    brief: "LinkedIn post about Q2 product launch",
    output_text: "🚀 Big news from the team! After months of R&D, we're thrilled to announce the launch of our AI-powered campaign builder. It writes, reviews, and optimizes your campaigns automatically...",
    review_scores: { brand_fit: 9, clarity: 8, cta_strength: 7, tone: 8 },
    created_at: "2026-04-07T14:30:00Z",
    status: "approved",
    task_template_id: "linkedin_post",
  },
  {
    id: "job-2",
    brief: "Series A funding announcement",
    output_text: "We're excited to share that Zeta has raised $12M in Series A funding led by Acme Ventures. This milestone fuels our mission to make AI-powered marketing accessible to every team...",
    review_scores: { brand_fit: 9, clarity: 9, cta_strength: 8, tone: 9 },
    created_at: "2026-04-05T09:15:00Z",
    status: "approved",
    task_template_id: "linkedin_post",
  },
  {
    id: "job-3",
    brief: "Blog post: 5 ways AI changes content marketing",
    output_text: "Content marketing is evolving rapidly. AI agents are transforming how teams ideate, draft, review, and optimize content. Here are 5 ways this technology is reshaping the landscape...",
    review_scores: { brand_fit: 8, clarity: 9, cta_strength: 6, tone: 8 },
    created_at: "2026-04-03T11:00:00Z",
    status: "approved",
    task_template_id: "blog_post",
  },
  {
    id: "job-4",
    brief: "Email welcome sequence for trial users",
    output_text: "Subject: Welcome to Zeta — let's get you started\n\nHi {{first_name}},\n\nWelcome aboard! You've just unlocked access to an entire AI marketing agency...",
    review_scores: { brand_fit: 7, clarity: 8, cta_strength: 9, tone: 7 },
    created_at: "2026-04-01T16:45:00Z",
    status: "approved",
    task_template_id: "email_sequence",
  },
  {
    id: "job-5",
    brief: "Ad copy for Google Search — campaign builder",
    output_text: "AI Marketing That Works | Zeta\nAutomate campaigns from brief to publish. AI agents write, review & optimize.\nStart Free Trial →",
    review_scores: { brand_fit: 8, clarity: 9, cta_strength: 9, tone: 7 },
    created_at: "2026-03-28T10:00:00Z",
    status: "approved",
    task_template_id: "ad_copy",
  },
];

/* ─── Component ─────────────────────────────────────────────────── */

export default function AgentProfilePage() {
  const params = useParams<{ name: string }>();
  const { online } = useBackend();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [tab, setTab] = useState<Tab>("profile");
  const [jobScope, setJobScope] = useState<"user" | "org">("user");

  const showDemo = !online;

  useEffect(() => {
    if (!params.name) return;

    if (online) {
      futureAgents.get(params.name).then(setAgent).catch(() => {});
    } else {
      // Fallback to demo data
      setAgent(DEMO_AGENTS[params.name] || DEMO_AGENTS.senior_copywriter);
    }
  }, [params.name, online]);

  useEffect(() => {
    if (!params.name) return;

    if (online) {
      futureAgents.jobs(params.name, jobScope).then(setJobs).catch(() => {});
    } else {
      setJobs(DEMO_JOBS);
    }
  }, [params.name, jobScope, online]);

  if (!agent) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">
        Loading agent...
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      {/* Back link */}
      <Link
        href="/future/agents"
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4"
      >
        <ArrowLeft className="w-4 h-4" /> All Agents
      </Link>

      {/* Header */}
      <div className="flex items-start gap-4 mb-6">
        <span className="text-4xl">{agent.avatar_emoji}</span>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{agent.title}</h1>
          <div className="text-sm text-gray-500 capitalize">
            {agent.department} • Node: <code className="text-xs bg-gray-100 px-1 rounded">{agent.node_name}</code>
          </div>
          {agent.reports_to && (
            <div className="text-xs text-gray-400 mt-1">
              Reports to: <span className="font-medium">{agent.reports_to}</span>
            </div>
          )}
        </div>
      </div>

      {showDemo && (
        <DemoBanner
          feature="Agent Profile"
          compact
        />
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b mb-4">
        {TABS.map((t) => {
          const Icon = t.icon;
          return (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={clsx(
                "flex items-center gap-1.5 px-3 py-2 text-sm border-b-2 -mb-px transition-colors",
                tab === t.key
                  ? "border-blue-600 text-blue-600 font-medium"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              )}
            >
              <Icon className="w-4 h-4" />
              {t.label}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      <div className="mt-4">
        {tab === "profile" && (
          <div className="space-y-4">
            <Section title="Responsibilities">
              {agent.responsibilities.length > 0 ? (
                <ul className="list-disc list-inside space-y-1 text-sm text-gray-600">
                  {agent.responsibilities.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-gray-400">Not specified.</p>
              )}
            </Section>
          </div>
        )}

        {tab === "jobs" && (
          <div>
            {/* Scope toggle */}
            <div className="flex gap-2 mb-4">
              <button
                onClick={() => setJobScope("user")}
                className={clsx(
                  "text-xs px-3 py-1 rounded-full border",
                  jobScope === "user"
                    ? "bg-blue-600 text-white border-blue-600"
                    : "bg-white text-gray-600 border-gray-200"
                )}
              >
                My Jobs
              </button>
              <button
                onClick={() => setJobScope("org")}
                className={clsx(
                  "text-xs px-3 py-1 rounded-full border",
                  jobScope === "org"
                    ? "bg-blue-600 text-white border-blue-600"
                    : "bg-white text-gray-600 border-gray-200"
                )}
              >
                Org-wide
              </button>
            </div>

            {jobs.length === 0 ? (
              <p className="text-sm text-gray-400">No jobs recorded yet.</p>
            ) : (
              <div className="space-y-3">
                {jobs.map((job) => (
                  <div key={job.id} className="bg-white border rounded-lg p-3">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-gray-800 truncate flex-1">
                        {job.brief}
                      </span>
                      <span
                        className={clsx(
                          "text-xs px-2 py-0.5 rounded-full ml-2",
                          job.status === "approved"
                            ? "bg-green-100 text-green-700"
                            : "bg-gray-100 text-gray-500"
                        )}
                      >
                        {job.status}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 line-clamp-2 mb-2">
                      {job.output_text}
                    </p>
                    {job.review_scores && Object.keys(job.review_scores).length > 0 && (
                      <div className="flex gap-1 flex-wrap">
                        {Object.entries(job.review_scores).map(([k, v]) => (
                          <span
                            key={k}
                            className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded"
                          >
                            {k}: {v}/10
                          </span>
                        ))}
                      </div>
                    )}
                    <div className="text-xs text-gray-400 mt-2">
                      {new Date(job.created_at).toLocaleDateString()}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {showDemo && (
              <p className="text-[10px] text-gray-400 text-center mt-4">
                Mock data — will be replaced with real job history once content is generated.
              </p>
            )}
          </div>
        )}

        {tab === "skills" && (
          <Section title="Expertise Areas">
            {agent.expertise.length > 0 ? (
              <div className="flex gap-2 flex-wrap">
                {agent.expertise.map((e, i) => (
                  <span
                    key={i}
                    className="text-sm bg-blue-50 text-blue-700 px-3 py-1 rounded-full"
                  >
                    {e}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-400">No expertise listed.</p>
            )}
          </Section>
        )}

        {tab === "connections" && (
          <Section title="Works With">
            {agent.interacts_with.length > 0 ? (
              <div className="flex gap-2 flex-wrap">
                {agent.interacts_with.map((c, i) => (
                  <Link
                    key={i}
                    href={`/future/agents/${c}`}
                    className="text-sm bg-gray-100 text-gray-700 px-3 py-1 rounded-full hover:bg-gray-200"
                  >
                    {c}
                  </Link>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-400">No connections specified.</p>
            )}
          </Section>
        )}

        {tab === "prompt" && (
          <Section title="System Prompt / Persona">
            {agent.persona_prompt ? (
              <pre className="text-sm text-gray-700 bg-gray-50 border rounded-lg p-4 whitespace-pre-wrap font-mono">
                {agent.persona_prompt}
              </pre>
            ) : (
              <p className="text-sm text-gray-400">
                This agent uses the default persona from the agency manifest.
              </p>
            )}
          </Section>
        )}
      </div>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h3 className="text-sm font-medium text-gray-700 mb-2">{title}</h3>
      {children}
    </div>
  );
}
