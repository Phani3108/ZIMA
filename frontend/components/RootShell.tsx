"use client";

import AgentSidebar, { type AgentNavItem } from "@/components/future/AgentSidebar";

/* ─── Default agent list (demo) ─────────────────────────────────
   When backend is online, replace with /future/agents API.
   NEXT_PUBLIC_AGENT_FILTER env var can scope to a subset.
─────────────────────────────────────────────────────────────────── */
const ALL_AGENTS: AgentNavItem[] = [
  { name: "design",            label: "Design Agent",        avatar: "🖌️", status: "idle" },
  { name: "copy",              label: "Copywriter Agent",    avatar: "✍️", status: "idle" },
  { name: "seo",               label: "SEO Agent",           avatar: "🔎", status: "idle" },
  { name: "pm",                label: "Project Manager",     avatar: "📋", status: "idle" },
  { name: "competitive_intel", label: "Competitive Analyst", avatar: "🕵️", status: "idle" },
  { name: "product_marketing", label: "Product Marketer",    avatar: "🚀", status: "idle" },
  { name: "review",            label: "Quality Reviewer",    avatar: "📑", status: "idle" },
  { name: "research",          label: "Research Analyst",    avatar: "📊", status: "idle" },
];

function getVisibleAgents(): AgentNavItem[] {
  const filter = process.env.NEXT_PUBLIC_AGENT_FILTER;
  if (!filter) return ALL_AGENTS;
  const allowed = filter.split(",").map((s) => s.trim().toLowerCase());
  return ALL_AGENTS.filter((a) => allowed.includes(a.name));
}

export default function RootShell({ children }: { children: React.ReactNode }) {
  const agents = getVisibleAgents();

  return (
    <>
      <AgentSidebar agents={agents} pendingApprovals={0} />
      <main className="flex-1 overflow-y-auto flex flex-col">{children}</main>
    </>
  );
}
