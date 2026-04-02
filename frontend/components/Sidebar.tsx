"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  MessageCircle, Settings, Upload, BarChart2, Zap,
  Sparkles, GitBranch, LayoutDashboard, FolderKanban,
  Brain, ListTodo, CalendarClock, FlaskConical,
  DollarSign, Users, ChevronDown,
} from "lucide-react";
import clsx from "clsx";
import NotificationBell from "@/components/NotificationBell";

/* ─── Navigation structure ──────────────────────────────────────── */

type NavItem = { href: string; label: string; icon: any };
type NavGroup = { key: string; label: string; items: NavItem[] };

const TOP_NAV: NavItem[] = [
  { href: "/chat",      label: "Chat",      icon: MessageCircle },
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/tasks",     label: "Tasks",     icon: ListTodo },
];

const GROUPS: NavGroup[] = [
  {
    key: "build",
    label: "Build",
    items: [
      { href: "/skills",    label: "Skills",    icon: Sparkles },
      { href: "/workflows", label: "Workflows", icon: GitBranch },
      { href: "/programs",  label: "Programs",  icon: FolderKanban },
    ],
  },
  {
    key: "optimize",
    label: "Optimize",
    items: [
      { href: "/brain",       label: "Brain",       icon: Brain },
      { href: "/analytics",   label: "Analytics",   icon: BarChart2 },
      { href: "/experiments", label: "Experiments", icon: FlaskConical },
      { href: "/costs",       label: "Costs",       icon: DollarSign },
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

function NavLink({ href, label, icon: Icon, active }: NavItem & { active: boolean }) {
  return (
    <Link
      href={href}
      className={clsx(
        "flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors",
        active
          ? "bg-blue-50 text-brand font-medium"
          : "text-gray-600 hover:bg-gray-100"
      )}
    >
      <Icon size={15} />
      {label}
    </Link>
  );
}

export default function Sidebar() {
  const path = usePathname();

  // Auto-expand the group that contains the current page
  const activeGroupKey = GROUPS.find((g) =>
    g.items.some((i) => path?.startsWith(i.href))
  )?.key;

  const [open, setOpen] = useState<Record<string, boolean>>(() => {
    if (typeof window === "undefined") return {};
    try {
      return JSON.parse(localStorage.getItem("zima_nav") || "{}");
    } catch { return {}; }
  });

  // Ensure the active group is always open
  useEffect(() => {
    if (activeGroupKey && !open[activeGroupKey]) {
      setOpen((o) => ({ ...o, [activeGroupKey]: true }));
    }
  }, [activeGroupKey]);

  const toggle = (key: string) => {
    setOpen((prev) => {
      const next = { ...prev, [key]: !prev[key] };
      localStorage.setItem("zima_nav", JSON.stringify(next));
      return next;
    });
  };

  return (
    <aside className="w-52 bg-white border-r border-gray-200 flex flex-col py-4 px-3 shrink-0">
      {/* Logo */}
      <div className="flex items-center justify-between px-2 mb-6">
        <div className="flex items-center gap-2">
          <Zap size={20} className="text-brand" />
          <span className="font-semibold text-gray-800 text-sm">Zeta IMA</span>
        </div>
        <NotificationBell />
      </div>

      <nav className="flex-1 space-y-0.5 overflow-y-auto">
        {/* Top-level links */}
        {TOP_NAV.map((item) => (
          <NavLink key={item.href} {...item} active={!!path?.startsWith(item.href)} />
        ))}

        {/* Collapsible groups */}
        {GROUPS.map((group) => {
          const isOpen = open[group.key] ?? false;
          const hasActive = group.items.some((i) => path?.startsWith(i.href));

          return (
            <div key={group.key} className="mt-3">
              <button
                onClick={() => toggle(group.key)}
                className={clsx(
                  "flex items-center justify-between w-full px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider rounded-md transition-colors",
                  hasActive ? "text-brand" : "text-gray-400 hover:text-gray-600"
                )}
              >
                {group.label}
                <ChevronDown
                  size={12}
                  className={clsx("transition-transform", isOpen && "rotate-180")}
                />
              </button>
              {isOpen && (
                <div className="mt-0.5 space-y-0.5">
                  {group.items.map((item) => (
                    <NavLink key={item.href} {...item} active={!!path?.startsWith(item.href)} />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </nav>

      <div className="text-xs text-gray-300 px-2">v0.7.0</div>
    </aside>
  );
}
