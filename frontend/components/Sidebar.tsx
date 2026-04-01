"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  MessageCircle, Settings, Upload, BarChart2, Zap,
  Sparkles, GitBranch, LayoutDashboard, FolderKanban,
  Brain, ListTodo,
} from "lucide-react";
import clsx from "clsx";
import NotificationBell from "@/components/NotificationBell";

const NAV = [
  { href: "/chat",       label: "Chat",       icon: MessageCircle },
  { href: "/skills",     label: "Skills",     icon: Sparkles },
  { href: "/workflows",  label: "Workflows",  icon: GitBranch },
  { href: "/programs",   label: "Programs",   icon: FolderKanban },
  { href: "/brain",      label: "Brain",      icon: Brain },
  { href: "/dashboard",  label: "Dashboard",  icon: LayoutDashboard },
  { href: "/ingest",     label: "Ingest",     icon: Upload },
  { href: "/analytics",  label: "Analytics",  icon: BarChart2 },
  { href: "/settings",   label: "Settings",   icon: Settings },
];

export default function Sidebar() {
  const path = usePathname();
  return (
    <aside className="w-52 bg-white border-r border-gray-200 flex flex-col py-4 px-3 shrink-0">
      <div className="flex items-center justify-between px-2 mb-6">
        <div className="flex items-center gap-2">
          <Zap size={20} className="text-brand" />
          <span className="font-semibold text-gray-800 text-sm">Zeta IMA</span>
        </div>
        <NotificationBell />
      </div>
      <nav className="space-y-1 flex-1">
        {NAV.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={clsx(
              "flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors",
              path?.startsWith(href)
                ? "bg-blue-50 text-brand font-medium"
                : "text-gray-600 hover:bg-gray-100"
            )}
          >
            <Icon size={15} />
            {label}
          </Link>
        ))}
      </nav>
      <div className="text-xs text-gray-300 px-2">v0.5.0</div>
    </aside>
  );
}
