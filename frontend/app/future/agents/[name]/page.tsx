"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Briefcase, BookOpen, Users, MessageSquare, History } from "lucide-react";
import clsx from "clsx";
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

export default function AgentProfilePage() {
  const params = useParams<{ name: string }>();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [tab, setTab] = useState<Tab>("profile");
  const [jobScope, setJobScope] = useState<"user" | "org">("user");

  useEffect(() => {
    if (!params.name) return;
    futureAgents.get(params.name).then(setAgent).catch(() => {});
  }, [params.name]);

  useEffect(() => {
    if (!params.name) return;
    futureAgents
      .jobs(params.name, jobScope)
      .then(setJobs)
      .catch(() => {});
  }, [params.name, jobScope]);

  if (!agent) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">
        Loading agent...
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
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
          <h1 className="text-xl font-semibold text-gray-800">{agent.title}</h1>
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
                          "text-xs px-2 py-0.5 rounded-full",
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
