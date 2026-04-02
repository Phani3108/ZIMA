"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Users, Plus, RefreshCw, Loader2, Trash2, UserPlus,
  Shield, Crown, UserCircle,
} from "lucide-react";
import clsx from "clsx";
import { teams } from "@/lib/api";
import { useBackend } from "@/lib/useBackend";
import OfflineBanner from "@/components/OfflineBanner";
import DemoBanner from "@/components/DemoBanner";

type Member = {
  user_id: string;
  display_name: string;
  email: string;
  role: string;
  joined_at: string;
};

type Team = {
  id: string;
  name: string;
  description: string;
  created_by: string;
  members: Member[];
  created_at: string;
};

const ROLE_ICONS: Record<string, any> = {
  admin: Crown,
  manager: Shield,
  member: UserCircle,
};

const ROLE_COLORS: Record<string, string> = {
  admin:      "bg-purple-100 text-purple-700",
  manager:    "bg-blue-100 text-blue-700",
  strategist: "bg-amber-100 text-amber-700",
  copywriter: "bg-green-100 text-green-700",
  designer:   "bg-pink-100 text-pink-700",
  member:     "bg-gray-100 text-gray-700",
};

export default function TeamsPage() {
  const { online, checking } = useBackend();
  const [allTeams, setAllTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Team | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ name: "", description: "" });
  const [addForm, setAddForm] = useState({ user_id: "", display_name: "", email: "", role: "member" });
  const [showAddMember, setShowAddMember] = useState(false);

  const load = useCallback(() => {
    if (!online) { setLoading(false); return; }
    setLoading(true);
    teams.list().then(setAllTeams).catch(() => {}).finally(() => setLoading(false));
  }, [online]);

  useEffect(() => { load(); }, [load]);

  if (!online && !checking) return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2 mb-4"><Users size={22} /> Teams</h1>
      <DemoBanner
        feature="Teams"
        steps={[
          "Start the backend and click 'New Team' to create a marketing team",
          "Add members with roles (admin, manager, strategist, copywriter, designer)",
          "Teams share context and can be assigned to workflows and programs",
        ]}
      />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[
          { id: "team1", name: "Content Team", description: "Blog posts, social copy, and email content creation", created_by: "phani", created_at: "2026-01-15T10:00:00Z", members: [
            { user_id: "u1", display_name: "Phani M.", email: "phani@zeta.ai", role: "admin", joined_at: "2026-01-15T10:00:00Z" },
            { user_id: "u2", display_name: "Sarah K.", email: "sarah@zeta.ai", role: "copywriter", joined_at: "2026-01-16T09:00:00Z" },
            { user_id: "u3", display_name: "Alex R.", email: "alex@zeta.ai", role: "strategist", joined_at: "2026-01-17T11:00:00Z" },
          ] },
          { id: "team2", name: "Design & Brand", description: "Visual assets, brand guidelines, and creative direction", created_by: "phani", created_at: "2026-02-01T08:00:00Z", members: [
            { user_id: "u1", display_name: "Phani M.", email: "phani@zeta.ai", role: "admin", joined_at: "2026-02-01T08:00:00Z" },
            { user_id: "u4", display_name: "Maya L.", email: "maya@zeta.ai", role: "designer", joined_at: "2026-02-02T10:00:00Z" },
          ] },
          { id: "team3", name: "Growth & SEO", description: "Keyword research, competitor analysis, and organic growth", created_by: "phani", created_at: "2026-02-10T09:00:00Z", members: [
            { user_id: "u5", display_name: "Jordan P.", email: "jordan@zeta.ai", role: "manager", joined_at: "2026-02-10T09:00:00Z" },
            { user_id: "u6", display_name: "Casey T.", email: "casey@zeta.ai", role: "member", joined_at: "2026-02-11T10:00:00Z" },
          ] },
        ].map((team) => {
          const RoleIcon = ROLE_ICONS["admin"] || UserCircle;
          return (
            <div key={team.id} className="bg-white border rounded-xl p-5">
              <h3 className="font-semibold text-gray-900">{team.name}</h3>
              <p className="text-xs text-gray-500 mt-0.5 mb-3">{team.description}</p>
              <div className="space-y-2">
                {team.members.map((m) => {
                  const MIcon = ROLE_ICONS[m.role] || UserCircle;
                  return (
                    <div key={m.user_id} className="flex items-center gap-2 text-sm">
                      <MIcon size={14} className="text-gray-400" />
                      <span className="text-gray-700">{m.display_name}</span>
                      <span className={clsx("text-[10px] px-1.5 py-0.5 rounded-full font-medium", ROLE_COLORS[m.role] || ROLE_COLORS.member)}>{m.role}</span>
                    </div>
                  );
                })}
              </div>
              <div className="text-[10px] text-gray-400 mt-3">{team.members.length} members · Created {new Date(team.created_at).toLocaleDateString()}</div>
            </div>
          );
        })}
      </div>
    </div>
  );

  const selectTeam = async (id: string) => {
    try {
      const t = await teams.get(id);
      setSelected(t);
    } catch { /* ignore */ }
  };

  const handleCreate = async () => {
    if (!form.name.trim()) return;
    setCreating(true);
    try {
      const t = await teams.create({ name: form.name, description: form.description });
      setForm({ name: "", description: "" });
      setShowCreate(false);
      load();
      selectTeam(t.id);
    } finally { setCreating(false); }
  };

  const handleAddMember = async () => {
    if (!selected || !addForm.user_id.trim()) return;
    await teams.addMember(selected.id, addForm);
    setAddForm({ user_id: "", display_name: "", email: "", role: "member" });
    setShowAddMember(false);
    selectTeam(selected.id);
    load();
  };

  const handleRemoveMember = async (userId: string) => {
    if (!selected) return;
    await teams.removeMember(selected.id, userId);
    selectTeam(selected.id);
    load();
  };

  const handleDeleteTeam = async (id: string) => {
    await teams.delete(id);
    if (selected?.id === id) setSelected(null);
    load();
  };

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Users size={22} /> Teams
          </h1>
          <p className="text-gray-500 text-sm mt-1">Manage teams, members, and role assignments.</p>
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="p-2 rounded-lg border hover:bg-gray-50"><RefreshCw size={16} /></button>
          <button onClick={() => setShowCreate(true)}
            className="flex items-center gap-1.5 px-3 py-2 bg-brand text-white rounded-lg text-sm font-medium hover:bg-blue-700">
            <Plus size={14} /> New Team
          </button>
        </div>
      </div>

      {showCreate && (
        <div className="bg-white border rounded-xl p-5 mb-6 shadow-sm">
          <h3 className="font-semibold mb-3 text-sm">Create Team</h3>
          <input placeholder="Team name" value={form.name}
            onChange={(e) => setForm(f => ({ ...f, name: e.target.value }))}
            className="w-full border rounded-lg px-3 py-2 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-brand" />
          <input placeholder="Description" value={form.description}
            onChange={(e) => setForm(f => ({ ...f, description: e.target.value }))}
            className="w-full border rounded-lg px-3 py-2 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-brand" />
          <div className="flex gap-2 justify-end">
            <button onClick={() => setShowCreate(false)} className="px-3 py-1.5 text-sm text-gray-500">Cancel</button>
            <button onClick={handleCreate} disabled={creating || !form.name.trim()}
              className="px-4 py-1.5 bg-brand text-white rounded-lg text-sm font-medium disabled:opacity-50">
              {creating ? "Creating..." : "Create"}
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Team list */}
        <div className="lg:col-span-1 space-y-2">
          {loading ? (
            <div className="flex justify-center py-10"><Loader2 className="animate-spin text-gray-400" size={20} /></div>
          ) : allTeams.length === 0 ? (
            <div className="text-center py-10 text-gray-400 text-sm">No teams yet.</div>
          ) : allTeams.map((t) => (
            <button key={t.id} onClick={() => selectTeam(t.id)}
              className={clsx("w-full text-left bg-white border rounded-xl p-4 hover:shadow-sm transition-shadow",
                selected?.id === t.id && "ring-2 ring-brand")}>
              <div className="font-medium text-sm text-gray-900">{t.name}</div>
              <p className="text-xs text-gray-500 line-clamp-1">{t.description || "No description"}</p>
              <span className="text-[11px] text-gray-400 mt-1 block">{t.members?.length ?? 0} members</span>
            </button>
          ))}
        </div>

        {/* Detail */}
        <div className="lg:col-span-2">
          {selected ? (
            <div className="bg-white border rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-900">{selected.name}</h3>
                <div className="flex gap-2">
                  <button onClick={() => setShowAddMember(true)}
                    className="flex items-center gap-1 px-3 py-1.5 bg-brand text-white rounded-lg text-xs font-medium hover:bg-blue-700">
                    <UserPlus size={12} /> Add Member
                  </button>
                  <button onClick={() => handleDeleteTeam(selected.id)}
                    className="flex items-center gap-1 px-3 py-1.5 text-red-500 border border-red-200 rounded-lg text-xs hover:bg-red-50">
                    <Trash2 size={12} /> Delete
                  </button>
                </div>
              </div>
              <p className="text-sm text-gray-500 mb-4">{selected.description}</p>

              {showAddMember && (
                <div className="border rounded-lg p-4 mb-4 bg-gray-50">
                  <div className="grid grid-cols-2 gap-2 mb-2">
                    <input placeholder="User ID" value={addForm.user_id}
                      onChange={(e) => setAddForm(f => ({ ...f, user_id: e.target.value }))}
                      className="border rounded-lg px-3 py-2 text-sm" />
                    <input placeholder="Display name" value={addForm.display_name}
                      onChange={(e) => setAddForm(f => ({ ...f, display_name: e.target.value }))}
                      className="border rounded-lg px-3 py-2 text-sm" />
                    <input placeholder="Email" value={addForm.email}
                      onChange={(e) => setAddForm(f => ({ ...f, email: e.target.value }))}
                      className="border rounded-lg px-3 py-2 text-sm" />
                    <select value={addForm.role}
                      onChange={(e) => setAddForm(f => ({ ...f, role: e.target.value }))}
                      className="border rounded-lg px-3 py-2 text-sm">
                      <option value="member">Member</option>
                      <option value="copywriter">Copywriter</option>
                      <option value="designer">Designer</option>
                      <option value="strategist">Strategist</option>
                      <option value="manager">Manager</option>
                      <option value="admin">Admin</option>
                    </select>
                  </div>
                  <div className="flex gap-2 justify-end">
                    <button onClick={() => setShowAddMember(false)} className="text-xs text-gray-500">Cancel</button>
                    <button onClick={handleAddMember} disabled={!addForm.user_id.trim()}
                      className="px-3 py-1 bg-brand text-white rounded-lg text-xs disabled:opacity-50">Add</button>
                  </div>
                </div>
              )}

              <div className="space-y-2">
                {(selected.members ?? []).map((m) => {
                  const RoleIcon = ROLE_ICONS[m.role] ?? UserCircle;
                  return (
                    <div key={m.user_id} className="flex items-center gap-3 py-2 border-b last:border-0">
                      <RoleIcon size={16} className="text-gray-400" />
                      <div className="flex-1 min-w-0">
                        <span className="text-sm font-medium text-gray-900">{m.display_name || m.user_id}</span>
                        {m.email && <span className="text-xs text-gray-400 ml-2">{m.email}</span>}
                      </div>
                      <span className={clsx("px-2 py-0.5 rounded-full text-[10px] font-medium", ROLE_COLORS[m.role] ?? ROLE_COLORS.member)}>
                        {m.role}
                      </span>
                      <button onClick={() => handleRemoveMember(m.user_id)}
                        className="text-red-400 hover:text-red-600 p-1">
                        <Trash2 size={12} />
                      </button>
                    </div>
                  );
                })}
                {(selected.members ?? []).length === 0 && (
                  <div className="text-center py-6 text-gray-400 text-sm">No members yet.</div>
                )}
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center py-20 text-gray-400 text-sm">
              Select a team to view members.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
