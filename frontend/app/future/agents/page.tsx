"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Users, Search, Briefcase } from "lucide-react";
import clsx from "clsx";
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

export default function FutureAgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [search, setSearch] = useState("");
  const [deptFilter, setDeptFilter] = useState<string | null>(null);

  useEffect(() => {
    futureAgents.list().then(setAgents).catch(() => {});
  }, []);

  const departments = [...new Set(agents.map((a) => a.department))];

  const filtered = agents.filter((a) => {
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
    <div className="max-w-5xl mx-auto px-4 py-6">
      <h1 className="text-xl font-semibold text-gray-800 mb-1 flex items-center gap-2">
        <Users className="w-5 h-5" />
        Agent Directory
      </h1>
      <p className="text-sm text-gray-500 mb-6">
        Meet your agency team. Click any agent to view their full profile and job history.
      </p>

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
    </div>
  );
}
