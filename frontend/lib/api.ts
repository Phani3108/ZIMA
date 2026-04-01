/**
 * API client for Zeta IMA backend.
 * All calls go through Next.js rewrite proxy (/api/* → backend).
 */

const BASE = "/api";

async function fetchJSON<T = any>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json();
}

// ─── Skills ────────────────────────────────────────────────────────

export const skills = {
  list: () => fetchJSON("/skills"),
  get: (id: string) => fetchJSON(`/skills/${id}`),
  categories: () => fetchJSON("/skills/categories"),
  search: (q: string) => fetchJSON(`/skills/search?q=${encodeURIComponent(q)}`),
  getPrompt: (skillId: string, promptId: string) =>
    fetchJSON(`/skills/${skillId}/prompts/${promptId}`),
  execute: (skillId: string, body: {
    prompt_id: string;
    variables: Record<string, string>;
    name?: string;
  }) => fetchJSON(`/skills/${skillId}/execute`, {
    method: "POST",
    body: JSON.stringify(body),
  }),
};

// ─── Workflows ─────────────────────────────────────────────────────

export const workflows = {
  list: (status?: string) =>
    fetchJSON(`/workflows${status ? `?status=${status}` : ""}`),
  get: (id: string) => fetchJSON(`/workflows/${id}`),
  create: (body: {
    template_id: string;
    variables: Record<string, string>;
    name?: string;
    auto_start?: boolean;
  }) => fetchJSON("/workflows", { method: "POST", body: JSON.stringify(body) }),
  templates: () => fetchJSON("/workflows/templates"),
  advance: (id: string) =>
    fetchJSON(`/workflows/${id}/advance`, { method: "POST" }),
  approve: (workflowId: string, stageId: string, comment = "") =>
    fetchJSON(`/workflows/${workflowId}/stages/${stageId}/approve`, {
      method: "POST",
      body: JSON.stringify({ comment }),
    }),
  reject: (workflowId: string, stageId: string, comment = "") =>
    fetchJSON(`/workflows/${workflowId}/stages/${stageId}/reject`, {
      method: "POST",
      body: JSON.stringify({ comment }),
    }),
  retry: (workflowId: string, stageId: string, llm_override?: string) =>
    fetchJSON(`/workflows/${workflowId}/stages/${stageId}/retry`, {
      method: "POST",
      body: JSON.stringify({ llm_override }),
    }),
  edit: (workflowId: string, stageId: string, instruction: string) =>
    fetchJSON(`/workflows/${workflowId}/stages/${stageId}/edit`, {
      method: "POST",
      body: JSON.stringify({ instruction }),
    }),
  cancel: (id: string) =>
    fetchJSON(`/workflows/${id}`, { method: "DELETE" }),
};

// ─── Dashboard ─────────────────────────────────────────────────────

export const dashboard = {
  summary: () => fetchJSON("/dashboard/summary"),
  activity: (limit = 30) => fetchJSON(`/dashboard/activity?limit=${limit}`),
  stuck: () => fetchJSON("/dashboard/stuck"),
  agents: () => fetchJSON("/dashboard/agents"),
  skillsUsage: (days = 30) => fetchJSON(`/dashboard/skills-usage?days=${days}`),
};

// ─── Settings ──────────────────────────────────────────────────────

export const settings = {
  listIntegrations: () => fetchJSON("/settings/integrations"),
  setKeys: (name: string, keys: Record<string, string>) =>
    fetchJSON(`/settings/integrations/${name}`, {
      method: "POST",
      body: JSON.stringify({ keys }),
    }),
  deleteIntegration: (name: string) =>
    fetchJSON(`/settings/integrations/${name}`, { method: "DELETE" }),
  testIntegration: (name: string) =>
    fetchJSON(`/settings/integrations/${name}/test`, { method: "POST" }),
  listActions: () => fetchJSON("/settings/actions"),
};

// ─── Programs ──────────────────────────────────────────────────────

export const programs = {
  list: (status?: string) =>
    fetchJSON(`/programs${status ? `?status=${status}` : ""}`),
  get: (id: string) => fetchJSON(`/programs/${id}`),
  create: (body: { name: string; description?: string; target_date?: string; tags?: string[] }) =>
    fetchJSON("/programs", { method: "POST", body: JSON.stringify(body) }),
  timeline: (id: string) => fetchJSON(`/programs/${id}/timeline`),
  advanceAll: (id: string) =>
    fetchJSON(`/programs/${id}/advance-all`, { method: "POST" }),
  cancel: (id: string) =>
    fetchJSON(`/programs/${id}`, { method: "DELETE" }),
};

// ─── Notifications ─────────────────────────────────────────────────

export const notificationsApi = {
  list: (limit = 50, unreadOnly = false) =>
    fetchJSON(`/notifications?limit=${limit}&unread_only=${unreadOnly}`),
  unreadCount: () => fetchJSON("/notifications/unread-count"),
  markRead: (id: string) =>
    fetchJSON(`/notifications/${id}/read`, { method: "POST" }),
  markAllRead: () =>
    fetchJSON("/notifications/read-all", { method: "POST" }),
};

// ─── Audit ─────────────────────────────────────────────────────────

export const audit = {
  recent: (limit = 50) => fetchJSON(`/audit?limit=${limit}`),
  forResource: (type: string, id: string) =>
    fetchJSON(`/audit/resource/${type}/${id}`),
  forWorkflow: (workflowId: string) =>
    fetchJSON(`/audit/workflow/${workflowId}`),
};

// ─── Tasks (Orchestrator Queue) ─────────────────────────────────────

export const tasks = {
  list: (status?: string, pipeline?: string, limit = 50) => {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    if (pipeline) params.set("pipeline", pipeline);
    params.set("limit", String(limit));
    return fetchJSON(`/tasks?${params}`);
  },
  get: (id: string) => fetchJSON(`/tasks/${id}`),
  create: (body: {
    title: string;
    description: string;
    priority?: number;
    pipeline_name?: string;
  }) => fetchJSON("/tasks", { method: "POST", body: JSON.stringify(body) }),
  update: (id: string, body: { status?: string; priority?: number }) =>
    fetchJSON(`/tasks/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  cancel: (id: string) => fetchJSON(`/tasks/${id}`, { method: "DELETE" }),
  pipelines: () => fetchJSON("/tasks/pipelines"),
};

// ─── Agency Brain ───────────────────────────────────────────────────

export const brain = {
  query: (q: string, options?: { category?: string; level?: string; top_k?: number }) => {
    const params = new URLSearchParams({ q });
    if (options?.category) params.set("category", options.category);
    if (options?.level) params.set("level", options.level);
    if (options?.top_k) params.set("top_k", String(options.top_k));
    return fetchJSON(`/brain/query?${params}`);
  },
  contribute: (body: {
    text: string;
    category?: string;
    level?: string;
    confidence?: number;
    tags?: string[];
  }) => fetchJSON("/brain/contribute", { method: "POST", body: JSON.stringify(body) }),
  conflicts: () => fetchJSON("/brain/conflicts"),
  resolveConflict: (id: string, resolution: "accept" | "reject") =>
    fetchJSON(`/brain/conflicts/${id}/resolve`, {
      method: "POST",
      body: JSON.stringify({ resolution }),
    }),
  compact: () => fetchJSON("/brain/compact", { method: "POST" }),
};

// ─── Distill ────────────────────────────────────────────────────────

export const distill = {
  session: (sessionId: string, messages: Array<{ role: string; content: string }>) =>
    fetchJSON(`/distill/session/${sessionId}`, {
      method: "POST",
      body: JSON.stringify({ messages }),
    }),
  signals: (level = "zeta", top_k = 50) =>
    fetchJSON(`/distill/signals?level=${level}&top_k=${top_k}`),
  sprint: (days_back = 7) =>
    fetchJSON(`/distill/sprint?days_back=${days_back}`, { method: "POST" }),
};

// ─── User Skills (Codable) ──────────────────────────────────────────

export const userSkills = {
  list: (includeShared = true) =>
    fetchJSON(`/user-skills?include_shared=${includeShared}`),
  get: (id: string) => fetchJSON(`/user-skills/${id}`),
  create: (body: {
    name: string;
    description?: string;
    code: string;
    is_shared?: boolean;
    tags?: string[];
  }) => fetchJSON("/user-skills", { method: "POST", body: JSON.stringify(body) }),
  update: (id: string, body: {
    name?: string;
    description?: string;
    code?: string;
    is_shared?: boolean;
    tags?: string[];
  }) => fetchJSON(`/user-skills/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  delete: (id: string) => fetchJSON(`/user-skills/${id}`, { method: "DELETE" }),
  execute: (id: string, inputs: Record<string, unknown> = {}) =>
    fetchJSON(`/user-skills/${id}/execute`, {
      method: "POST",
      body: JSON.stringify({ inputs }),
    }),
  validate: (code: string) =>
    fetchJSON("/user-skills/validate", {
      method: "POST",
      body: JSON.stringify({ code }),
    }),
};
