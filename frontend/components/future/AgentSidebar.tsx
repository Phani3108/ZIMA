"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import clsx from "clsx";
import { ClipboardCheck, FlaskConical, Settings } from "lucide-react";

export type AgentNavItem = {
  name: string;       // url-slug (e.g. "design")
  label: string;      // display name (e.g. "Design Agent")
  avatar: string;     // emoji
  status: "idle" | "working" | "waiting";
  activeTaskCount?: number;
};

const STATUS_DOT: Record<string, string> = {
  idle:    "bg-gray-300",
  working: "bg-blue-500 animate-pulse",
  waiting: "bg-amber-400",
};

const STATUS_TEXT: Record<string, string> = {
  idle:    "Idle",
  working: "Working",
  waiting: "Waiting",
};

type Props = {
  agents: AgentNavItem[];
  pendingApprovals?: number;
};

export default function AgentSidebar({ agents, pendingApprovals = 0 }: Props) {
  const path = usePathname();

  return (
    <aside className="w-56 bg-white border-r border-gray-200 flex flex-col shrink-0 h-full">
      {/* Header */}
      <div className="px-4 pt-5 pb-3 border-b border-gray-100">
        <Link href="/future/agent" className="flex items-center gap-2">
          <div className="w-7 h-7 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center">
            <span className="text-white text-xs font-bold">Z</span>
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-800 leading-none">Zeta Agents</p>
            <p className="text-[10px] text-gray-400 mt-0.5">AI Marketing Agency</p>
          </div>
        </Link>
      </div>

      {/* Agent list */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
        <p className="px-2 mb-2 text-[10px] font-semibold uppercase tracking-wider text-gray-400">
          Agents
        </p>
        {agents.map((agent) => {
          const active = path === `/future/agent/${agent.name}`;
          return (
            <Link
              key={agent.name}
              href={`/future/agent/${agent.name}`}
              className={clsx(
                "flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm transition-colors group",
                active
                  ? "bg-blue-50 border-l-2 border-blue-600 text-blue-700 font-medium"
                  : "text-gray-600 hover:bg-gray-50",
              )}
            >
              <span className="text-lg leading-none">{agent.avatar}</span>
              <div className="flex-1 min-w-0">
                <p className="text-[13px] truncate">{agent.label}</p>
              </div>
              <div className="flex items-center gap-1.5 shrink-0">
                {agent.activeTaskCount && agent.activeTaskCount > 0 ? (
                  <span className="text-[10px] font-bold bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded-full">
                    {agent.activeTaskCount}
                  </span>
                ) : null}
                <span className={clsx("w-2 h-2 rounded-full", STATUS_DOT[agent.status])} title={STATUS_TEXT[agent.status]} />
              </div>
            </Link>
          );
        })}
      </nav>

      {/* Footer links */}
      <div className="border-t border-gray-100 px-2 py-3 space-y-0.5">
        <Link
          href="/future/approvals"
          className={clsx(
            "flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm transition-colors",
            path === "/future/approvals"
              ? "bg-blue-50 text-blue-700 font-medium"
              : "text-gray-600 hover:bg-gray-50",
          )}
        >
          <ClipboardCheck className="w-4 h-4" />
          <span className="flex-1">Approvals</span>
          {pendingApprovals > 0 && (
            <span className="text-[10px] font-bold bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded-full">
              {pendingApprovals}
            </span>
          )}
        </Link>
        <Link
          href="/future/experiments"
          className={clsx(
            "flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm transition-colors",
            path?.startsWith("/future/experiments")
              ? "bg-blue-50 text-blue-700 font-medium"
              : "text-gray-600 hover:bg-gray-50",
          )}
        >
          <FlaskConical className="w-4 h-4" />
          Experiments
        </Link>
        <Link
          href="/settings"
          className="flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm text-gray-500 hover:bg-gray-50 transition-colors"
        >
          <Settings className="w-4 h-4" />
          Settings
        </Link>
      </div>
    </aside>
  );
}
