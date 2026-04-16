"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import {
  MessageCircle, Settings, Upload, BarChart2,
  Sparkles, GitBranch, LayoutDashboard, FolderKanban,
  Brain, ListTodo, CalendarClock, FlaskConical,
  DollarSign, Users, ChevronDown, Archive,
  MessageSquare, Share2, Rocket, Shield, UserCircle,
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
    key: "future",
    label: "Future",
    items: [
      { href: "/future/agent/design", label: "Agent Workspace", icon: Rocket },
      { href: "/future/chat",         label: "Future Chat",     icon: Rocket },
      { href: "/future/agents",       label: "Agent Directory",  icon: UserCircle },
      { href: "/future/approvals",    label: "Approvals",       icon: Shield },
    ],
  },
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
    key: "collaborate",
    label: "Collaborate",
    items: [
      { href: "/artifacts",      label: "Artifacts",      icon: Archive },
      { href: "/conversations",  label: "History",        icon: MessageSquare },
      { href: "/handoffs",       label: "Handoffs",       icon: Share2 },
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
        <Link href="/" className="flex items-center gap-2">
          <Image
            src="https://res.cloudinary.com/apideck/image/upload/v1618437828/icons/zeta-tech.jpg"
            alt="Zeta"
            width={24}
            height={24}
            className="rounded"
            unoptimized
          />
          <span className="font-semibold text-gray-800 text-sm">Zeta IMA</span>
        </Link>
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

      <div className="text-[10px] text-gray-300 px-2 leading-relaxed">
        <div>v0.7.0</div>
        <div className="mt-1">&copy; 2026 Better World Technology</div>
      </div>
    </aside>
  );
}
