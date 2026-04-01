"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Plus, FolderKanban, Loader2, ChevronRight,
  CheckCircle2, Clock, Target, CalendarDays,
} from "lucide-react";
import clsx from "clsx";

type Program = {
  id: string;
  name: string;
  description: string;
  campaign_id: string;
  status: string;
  target_date: string | null;
  tags: string[];
  workflow_count: number;
  completed_count: number;
  created_at: string;
};

export default function ProgramsPage() {
  const [programs, setPrograms] = useState<Program[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);

  const loadPrograms = () => {
    setLoading(true);
    fetch("/api/programs")
      .then((r) => r.json())
      .then((data) => { setPrograms(data); setLoading(false); })
      .catch(() => setLoading(false));
  };

  useEffect(() => { loadPrograms(); }, []);

  const createProgram = async (name: string, description: string, targetDate: string) => {
    await fetch("/api/programs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, description, target_date: targetDate || undefined }),
    });
    setShowCreate(false);
    loadPrograms();
  };

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Programs</h1>
          <p className="text-gray-500 mt-1 text-sm">
            Group related workflows into campaigns for unified tracking.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 bg-brand hover:bg-blue-700 text-white px-4 py-2 rounded-xl text-sm font-medium"
        >
          <Plus size={14} /> New Program
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="animate-spin text-gray-400" size={24} />
        </div>
      ) : programs.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <FolderKanban size={40} className="mx-auto mb-3 text-gray-300" />
          <p className="mb-1">No programs yet.</p>
          <p className="text-sm">Create a program to group related workflows together.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {programs.map((prog) => {
            const progress = prog.workflow_count > 0
              ? Math.round((prog.completed_count / prog.workflow_count) * 100)
              : 0;

            return (
              <Link
                key={prog.id}
                href={`/programs/${prog.id}`}
                className="group bg-white border rounded-xl p-5 hover:shadow-md hover:border-brand/30 transition-all"
              >
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="font-semibold text-gray-900">{prog.name}</h3>
                    {prog.description && (
                      <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{prog.description}</p>
                    )}
                  </div>
                  <ChevronRight size={14} className="text-gray-300 group-hover:text-brand" />
                </div>

                {/* Progress */}
                <div className="mb-3">
                  <div className="flex items-center justify-between text-[11px] text-gray-500 mb-1">
                    <span>{prog.completed_count}/{prog.workflow_count} workflows completed</span>
                    <span className="font-semibold">{progress}%</span>
                  </div>
                  <div className="bg-gray-100 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-brand h-full rounded-full transition-all"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                </div>

                {/* Meta */}
                <div className="flex items-center gap-4 text-[11px] text-gray-400">
                  <span className="flex items-center gap-1">
                    <Clock size={10} />
                    {new Date(prog.created_at).toLocaleDateString()}
                  </span>
                  {prog.target_date && (
                    <span className="flex items-center gap-1">
                      <Target size={10} />
                      Due: {new Date(prog.target_date).toLocaleDateString()}
                    </span>
                  )}
                  {prog.tags.length > 0 && (
                    <div className="flex gap-1">
                      {prog.tags.map((t) => (
                        <span key={t} className="bg-gray-100 px-1.5 py-0.5 rounded text-[10px]">{t}</span>
                      ))}
                    </div>
                  )}
                </div>
              </Link>
            );
          })}
        </div>
      )}

      {/* Create Modal */}
      {showCreate && (
        <CreateProgramModal
          onClose={() => setShowCreate(false)}
          onCreate={createProgram}
        />
      )}
    </div>
  );
}

function CreateProgramModal({
  onClose,
  onCreate,
}: {
  onClose: () => void;
  onCreate: (name: string, description: string, targetDate: string) => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [targetDate, setTargetDate] = useState("");

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-2xl w-full max-w-md mx-4 p-6" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">New Program</h2>

        <div className="space-y-3 mb-5">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Program Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Q2 Product Launch"
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What's this program about?"
              rows={3}
              className="w-full border rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-brand"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Target Date (optional)</label>
            <input
              type="date"
              value={targetDate}
              onChange={(e) => setTargetDate(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand"
            />
          </div>
        </div>

        <div className="flex gap-2">
          <button onClick={onClose} className="flex-1 border text-gray-600 py-2 rounded-xl text-sm hover:bg-gray-50">
            Cancel
          </button>
          <button
            onClick={() => onCreate(name, description, targetDate)}
            disabled={!name.trim()}
            className="flex-1 bg-brand text-white py-2 rounded-xl text-sm font-medium disabled:opacity-50"
          >
            Create Program
          </button>
        </div>
      </div>
    </div>
  );
}
