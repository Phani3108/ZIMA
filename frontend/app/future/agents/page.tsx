"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Users, Search, Briefcase, Bot, FileText, Star } from "lucide-react";
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
  avatar_emoji: string;
};

const DEPT_COLORS: Record<string, string> = {
  content: "bg-blue-100 text-blue-700",
  design: "bg-purple-100 text-purple-700",
  strategy: "bg-green-100 text-green-700",
  operations: "bg-amber-100 text-amber-700",
};

/* ─── Demo Data ─────────────────────────────────────────────────── */

const DEMO_AGENTS: Agent[] = [
  {
    id: "senior_copywriter",
    title: "Senior Copywriter",
    department: "content",
    node_name: "copy",
    responsibilities: ["Write on-brand marketing copy", "Adapt tone per channel", "Incorporate brand voice guidelines"],
    expertise: ["LinkedIn posts", "Blog articles", "Email sequences", "Ad copy"],
    avatar_emoji: "✍️",
  },
  {
    id: "quality_reviewer",
    title: "Quality Reviewer",
    department: "content",
    node_name: "review",
    responsibilities: ["Score drafts against brand rubric", "Check clarity and CTA strength", "Gate content quality"],
    expertise: ["Brand consistency", "Tone analysis", "Quality scoring"],
    avatar_emoji: "🔍",
  },
  {
    id: "seo_specialist",
    title: "SEO Specialist",
    department: "strategy",
    node_name: "seo",
    responsibilities: ["Optimize content for search", "Keyword analysis", "Meta tag generation"],
    expertise: ["Keyword research", "On-page SEO", "Content optimization"],
    avatar_emoji: "📈",
  },
  {
    id: "research_analyst",
    title: "Research Analyst",
    department: "strategy",
    node_name: "research",
    responsibilities: ["Search knowledge base", "Gather market intelligence", "Provide context for briefs"],
    expertise: ["Market research", "Competitive analysis", "Data synthesis"],
    avatar_emoji: "🔬",
  },
  {
    id: "project_manager",
    title: "Project Manager",
    department: "operations",
    node_name: "pm",
    responsibilities: ["Decompose briefs into tasks", "Create agent instructions", "Coordinate pipeline"],
    expertise: ["Task decomposition", "Brief analysis", "Workflow orchestration"],
    avatar_emoji: "📋",
  },
  {
    id: "creative_director",
    title: "Creative Director",
    department: "design",
    node_name: "design",
    responsibilities: ["Generate visual concepts", "Create design briefs", "Maintain visual brand"],
    expertise: ["Visual identity", "Layout design", "Brand imagery"],
    avatar_emoji: "🎨",
  },
  {
    id: "competitive_analyst",
    title: "Competitive Intelligence Analyst",
    department: "strategy",
    node_name: "competitive_intel",
    responsibilities: ["Monitor competitor activity", "Analyze market positioning", "Identify opportunities"],
    expertise: ["Competitive analysis", "Market trends", "SWOT analysis"],
    avatar_emoji: "🕵️",
  },
  {
    id: "cmo",
    title: "Chief Marketing Officer",
    department: "operations",
    node_name: "approval",
    responsibilities: ["Final content approval", "Brand strategy oversight", "Quality gate decisions"],
    expertise: ["Brand strategy", "Marketing leadership", "Content governance"],
    avatar_emoji: "👔",
  },
];

export default function FutureAgentsPage() {
  const { online } = useBackend();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [search, setSearch] = useState("");
  const [deptFilter, setDeptFilter] = useState<string | null>(null);

  useEffect(() => {
    if (online) {
      futureAgents.list().then(setAgents).catch(() => {});
    }
  }, [online]);

  const showDemo = !online || agents.length === 0;
  const displayAgents = showDemo ? DEMO_AGENTS : agents;
  const departments = [...new Set(displayAgents.map((a) => a.department))];

  const filtered = displayAgents.filter((a) => {
    if (deptFilter && a.department !== deptFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      return (
        a.title.toLowerCase().includes(q) ||
        a.expertise.some((e) => e.toLowerCase().includes(q))
      );
    }
    return true;
  });

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
        <Users className="w-5 h-5" />
        Agent Directory
      </h1>
      <p className="text-gray-500 mt-1 text-sm mb-6">
        Meet your AI marketing agency team — each agent has a clear role, expertise, and job history.
      </p>

      {showDemo && (
        <DemoBanner
          feature="Agent Directory"
          steps={[
            "Start the backend — agents are loaded from the agency_manifest.yaml",
            "Click any agent to see their full profile, system prompt, and job history",
            "Use the scope toggle on Job History to switch between personal and org-wide view",
          ]}
        />
      )}

      {/* Stats */}
      {showDemo && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <div className="bg-white border rounded-xl p-3">
            <div className="flex items-center gap-1.5 mb-1">
              <Bot size={13} className="text-gray-400" />
              <span className="text-[11px] text-gray-500 uppercase tracking-wider">Total Agents</span>
            </div>
            <div className="text-xl font-bold text-blue-600">{DEMO_AGENTS.length}</div>
          </div>
          <div className="bg-white border rounded-xl p-3">
            <div className="flex items-center gap-1.5 mb-1">
              <Briefcase size={13} className="text-gray-400" />
              <span className="text-[11px] text-gray-500 uppercase tracking-wider">Departments</span>
            </div>
            <div className="text-xl font-bold text-purple-600">4</div>
          </div>
          <div className="bg-white border rounded-xl p-3">
            <div className="flex items-center gap-1.5 mb-1">
              <FileText size={13} className="text-gray-400" />
              <span className="text-[11px] text-gray-500 uppercase tracking-wider">Jobs Completed</span>
            </div>
            <div className="text-xl font-bold text-green-600">142</div>
          </div>
          <div className="bg-white border rounded-xl p-3">
            <div className="flex items-center gap-1.5 mb-1">
              <Star size={13} className="text-gray-400" />
              <span className="text-[11px] text-gray-500 uppercase tracking-wider">Avg Quality</span>
            </div>
            <div className="text-xl font-bold text-amber-600">8.4/10</div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3 items-center mb-6 flex-wrap">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search agents..."
            className="w-full pl-9 pr-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="flex gap-1">
          <button
            onClick={() => setDeptFilter(null)}
            className={clsx(
              "text-xs px-3 py-1.5 rounded-full border",
              !deptFilter ? "bg-gray-800 text-white border-gray-800" : "bg-white text-gray-600 border-gray-200"
            )}
          >
            All
          </button>
          {departments.map((dept) => (
            <button
              key={dept}
              onClick={() => setDeptFilter((prev) => (prev === dept ? null : dept))}
              className={clsx(
                "text-xs px-3 py-1.5 rounded-full border capitalize",
                deptFilter === dept ? "bg-gray-800 text-white border-gray-800" : "bg-white text-gray-600 border-gray-200"
              )}
            >
              {dept}
            </button>
          ))}
        </div>
      </div>

      {/* Agent Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((agent) => (
          <Link
            key={agent.id}
            href={`/future/agents/${agent.id}`}
            className="block bg-white border rounded-xl p-4 hover:shadow-md transition-shadow"
          >
            <div className="flex items-start gap-3 mb-3">
              <span className="text-2xl">{agent.avatar_emoji}</span>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-gray-800 truncate">{agent.title}</div>
                <span
                  className={clsx(
                    "inline-block text-xs px-2 py-0.5 rounded-full mt-1 capitalize",
                    DEPT_COLORS[agent.department] || "bg-gray-100 text-gray-600"
                  )}
                >
                  {agent.department}
                </span>
              </div>
            </div>
            {agent.responsibilities.length > 0 && (
              <ul className="text-xs text-gray-500 space-y-0.5 mb-3">
                {agent.responsibilities.slice(0, 3).map((r, i) => (
                  <li key={i} className="truncate">
                    • {r}
                  </li>
                ))}
              </ul>
            )}
            {agent.expertise.length > 0 && (
              <div className="flex gap-1 flex-wrap">
                {agent.expertise.slice(0, 4).map((e, i) => (
                  <span key={i} className="text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">
                    {e}
                  </span>
                ))}
              </div>
            )}
          </Link>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-12 text-gray-400">
          <Briefcase className="w-8 h-8 mx-auto mb-2" />
          <div>No agents found.</div>
        </div>
      )}

      {showDemo && (
        <p className="text-[10px] text-gray-400 text-center mt-6">
          Mock data — will be replaced with real agent profiles once the backend is connected.
        </p>
      )}
    </div>
  );
}
