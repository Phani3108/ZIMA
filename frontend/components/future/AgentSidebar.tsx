"use client";

import { useState, useEffect } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import clsx from "clsx";
import {
  ClipboardCheck, FlaskConical, Settings, ChevronDown,
  Brain, BarChart2, DollarSign, Archive, MessageSquare,
  Share2, Users, CalendarClock, Upload, FolderKanban,
  Wrench,
} from "lucide-react";

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

/* ─── Collapsible groups shown below agents ──────────────────────── */
type NavItem = { href: string; label: string; icon: any };
type NavGroup = { key: string; label: string; items: NavItem[] };

const GROUPS: NavGroup[] = [
  {
    key: "optimize",
    label: "Optimize",
    items: [
      { href: "/brain",       label: "Brain",       icon: Brain },
      { href: "/analytics",   label: "Analytics",   icon: BarChart2 },
      { href: "/experiments", label: "Experiments",  icon: FlaskConical },
      { href: "/costs",       label: "Costs",       icon: DollarSign },
    ],
  },
  {
    key: "collaborate",
    label: "Collaborate",
    items: [
      { href: "/artifacts",      label: "Artifacts", icon: Archive },
      { href: "/conversations",  label: "History",   icon: MessageSquare },
      { href: "/handoffs",       label: "Handoffs",  icon: Share2 },
    ],
  },
  {
    key: "manage",
    label: "Manage",
    items: [
      { href: "/teams",     label: "Teams",     icon: Users },
      { href: "/schedules", label: "Schedules", icon: CalendarClock },
      { href: "/ingest",    label: "Ingest",    icon: Upload },
      { href: "/settings",  label: "Settings",  icon: Settings },
    ],
  },
];

type Props = {
  agents: AgentNavItem[];
  pendingApprovals?: number;
};

export default function AgentSidebar({ agents, pendingApprovals = 0 }: Props) {
  const path = usePathname();

  // Collapsible group state (persisted)
  const [open, setOpen] = useState<Record<string, boolean>>(() => {
    if (typeof window === "undefined") return {};
    try { return JSON.parse(localStorage.getItem("zima_future_nav") || "{}"); } catch { return {}; }
  });

  // Auto-expand group containing current path
  useEffect(() => {
    const activeKey = GROUPS.find((g) => g.items.some((i) => path?.startsWith(i.href)))?.key;
    if (activeKey && !open[activeKey]) {
      setOpen((o) => ({ ...o, [activeKey]: true }));
    }
  }, [path]);

  const toggle = (key: string) => {
    setOpen((prev) => {
      const next = { ...prev, [key]: !prev[key] };
      localStorage.setItem("zima_future_nav", JSON.stringify(next));
      return next;
    });
  };

  return (
    <aside className="w-56 bg-white border-r border-gray-200 flex flex-col shrink-0 h-full">
      {/* Header */}
      <div className="px-4 pt-5 pb-3 border-b border-gray-100">
        <Link href="/dashboard" className="flex items-center gap-2">
          <div className="w-7 h-7 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center">
            <span className="text-white text-xs font-bold">Z</span>
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-800 leading-none">Zeta IMA</p>
            <p className="text-[10px] text-gray-400 mt-0.5">AI Marketing Agency</p>
          </div>
        </Link>
      </div>

      {/* Scrollable body */}
      <nav className="flex-1 overflow-y-auto py-3 px-2">
        {/* ── Agent list ───────────────────────────────────── */}
        <p className="px-2 mb-2 text-[10px] font-semibold uppercase tracking-wider text-gray-400">
          Agents
        </p>
        <div className="space-y-0.5">
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
        </div>

        {/* ── Approvals + Programs + Engine Config ─────────── */}
        <div className="mt-4 space-y-0.5">
          <Link
            href="/future/agent/design/config"
            className={clsx(
              "flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm transition-colors",
              path === "/future/agent/design/config"
                ? "bg-blue-50 text-blue-700 font-medium"
                : "text-gray-600 hover:bg-gray-50",
            )}
          >
            <Wrench className="w-4 h-4" />
            Engine Config
          </Link>
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
            href="/programs"
            className={clsx(
              "flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm transition-colors",
              path?.startsWith("/programs")
                ? "bg-blue-50 text-blue-700 font-medium"
                : "text-gray-600 hover:bg-gray-50",
            )}
          >
            <FolderKanban className="w-4 h-4" />
            Programs
          </Link>
        </div>

        {/* ── Collapsible groups: Optimize, Collaborate, Manage ── */}
        {GROUPS.map((group) => {
          const isOpen = open[group.key] ?? false;
          const hasActive = group.items.some((i) => path?.startsWith(i.href));

          return (
            <div key={group.key} className="mt-3">
              <button
                onClick={() => toggle(group.key)}
                className={clsx(
                  "flex items-center justify-between w-full px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-wider rounded-md transition-colors",
                  hasActive ? "text-blue-600" : "text-gray-400 hover:text-gray-600",
                )}
              >
                {group.label}
                <ChevronDown
                  className={clsx(
                    "w-3 h-3 transition-transform",
                    isOpen ? "rotate-0" : "-rotate-90",
                  )}
                />
              </button>
              {isOpen && (
                <div className="mt-1 space-y-0.5">
                  {group.items.map((item) => {
                    const active = path?.startsWith(item.href);
                    const Icon = item.icon;
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        className={clsx(
                          "flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-[13px] transition-colors",
                          active
                            ? "bg-blue-50 text-blue-700 font-medium"
                            : "text-gray-600 hover:bg-gray-50",
                        )}
                      >
                        <Icon className="w-3.5 h-3.5" />
                        {item.label}
                      </Link>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </nav>
    </aside>
  );
}
