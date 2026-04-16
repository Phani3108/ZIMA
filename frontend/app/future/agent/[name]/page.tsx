"use client";

import { useState, useCallback, useMemo, useRef, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Settings2, ExternalLink } from "lucide-react";
import clsx from "clsx";

import { useBackend } from "@/lib/useBackend";
import { futureAgents, designConfig } from "@/lib/api";
import DemoBanner from "@/components/DemoBanner";
import ToolCard from "@/components/future/ToolCard";
import CapabilityCard, { type Capability } from "@/components/future/CapabilityCard";
import TaskRow, { type RecentTask } from "@/components/future/TaskRow";
import CommandBar, { type ToolOption } from "@/components/future/CommandBar";
import AgentNarration, { type NarrationEntry } from "@/components/future/AgentNarration";
import AgentPlanCard, { type PlanStep } from "@/components/future/AgentPlanCard";
import AgentQuestionForm, { type AgentQuestion } from "@/components/future/AgentQuestionForm";
import IterationPreview from "@/components/future/IterationPreview";
import type { WorkflowStep } from "@/components/future/WorkflowMiniDiagram";

/* ═══════════════════════════════════════════════════════════════════
   DEMO DATA  — replaced by API when backend is online
   ═══════════════════════════════════════════════════════════════════ */

type AgentProfile = {
  name: string;
  label: string;
  title: string;
  avatar: string;
  department: string;
  departmentColor: string;
  persona: string;
  stats: { tasks: number; avgQuality: number; toolsConnected: number };
  tools: {
    id: string; name: string; icon: string; connected: boolean;
    setupUrl?: string; docsUrl?: string; fieldLabel?: string;
    fieldType?: "apikey" | "mcp";
  }[];
  capabilities: Capability[];
  recentTasks: RecentTask[];
};

const DEMO_AGENTS: Record<string, AgentProfile> = {
  design: {
    name: "design", label: "Design Agent", title: "Visual Designer", avatar: "🖌️",
    department: "Design", departmentColor: "bg-pink-100 text-pink-700",
    persona: "AI-powered visual creation, brand asset management, and iterative design refinement",
    stats: { tasks: 47, avgQuality: 8.6, toolsConnected: 3 },
    tools: [
      { id: "gemini_image", name: "Gemini Image", icon: "✨", connected: true, setupUrl: "https://aistudio.google.com", docsUrl: "https://ai.google.dev/gemini-api/docs/image-generation", fieldLabel: "API Key" },
      { id: "dalle", name: "DALL·E 3", icon: "🎨", connected: true, setupUrl: "https://platform.openai.com", docsUrl: "https://platform.openai.com/docs/guides/images", fieldLabel: "API Key" },
      { id: "canva", name: "Canva Connect", icon: "🎯", connected: false, docsUrl: "https://www.canva.dev/docs/connect/", fieldLabel: "API Key" },
      { id: "figma", name: "Figma", icon: "🔌", connected: false, docsUrl: "https://www.figma.com/developers", fieldLabel: "MCP URL", fieldType: "mcp" as const },
    ],
    capabilities: [
      {
        id: "social_visual", title: "Social Media Visual",
        description: "Create platform-optimized visuals for LinkedIn, Instagram, Twitter, and Facebook",
        steps: s("Brief", "Compose Prompt", "Generate Image", "Iterate", "Review", "Deliver"),
        tools: ["Gemini", "DALL·E"],
      },
      {
        id: "email_header", title: "Email Header",
        description: "Design responsive email headers aligned with campaign themes",
        steps: s("Brief", "Analyze Layout", "Generate", "Format", "Review"),
        tools: ["Gemini", "Canva"],
      },
      {
        id: "brand_asset", title: "Brand Asset Pack",
        description: "Generate cohesive brand asset variants — logos, banners, icons",
        steps: s("Brief", "Style Analysis", "Generate Variants", "Select", "Finalize"),
        tools: ["Gemini", "DALL·E"],
      },
      {
        id: "ad_creative", title: "Ad Creative",
        description: "Produce ad creatives with A/B variants for display and social",
        steps: s("Brief", "Audience Research", "Concept", "Generate", "A/B Variants", "Review"),
        tools: ["Gemini", "DALL·E"],
      },
      {
        id: "presentation_slide", title: "Presentation Slide",
        description: "Create individual presentation slides with modern layouts",
        steps: s("Brief", "Layout", "Generate", "Refine", "Export"),
        tools: ["Gemini"],
      },
    ],
    recentTasks: [
      { id: "t1", title: "LinkedIn Banner for Q2 Launch", status: "complete", time_ago: "2 hours ago", iterations: 3, score: 8.7, prompt: "Create a professional LinkedIn banner for our Q2 product launch. Use brand colors (blue/white), include the tagline \"Intelligence at Scale\", modern minimalist style, 1584x396px.", tools: ["Gemini", "Canva"], output_url: "/artifacts" },
      { id: "t2", title: "Instagram Story — Customer Testimonial", status: "complete", time_ago: "5 hours ago", iterations: 2, score: 9.1, prompt: "Design an Instagram story template for customer testimonials. Brand fonts, quote layout, photo placeholder, swipe-up CTA. 1080x1920.", tools: ["DALL·E"], output_url: "/artifacts" },
      { id: "t3", title: "Email Header — Spring Campaign", status: "awaiting_review", time_ago: "1 day ago", iterations: 1, score: null, prompt: "Create a spring-themed email header for our seasonal campaign. Include flowers/nature motifs, brand colors, 600x200px.", tools: ["Gemini"], output_url: "/artifacts" },
      { id: "t4", title: "Facebook Ad Set — Feature Highlight", status: "complete", time_ago: "2 days ago", iterations: 4, score: 7.9, prompt: "Generate 3 ad creative variants for Facebook highlighting our new analytics feature. Professional style, clear CTA, 1200x628px.", tools: ["Gemini", "DALL·E"], output_url: "/artifacts" },
      { id: "t5", title: "Slide Deck Cover — Annual Review", status: "complete", time_ago: "3 days ago", iterations: 2, score: 8.3, prompt: "Design a cover slide for our annual review deck. Modern, bold typography, brand gradients, 16:9 aspect ratio.", tools: ["Gemini"], output_url: "/artifacts" },
    ],
  },

  copy: {
    name: "copy", label: "Copywriter Agent", title: "Senior Copywriter", avatar: "✍️",
    department: "Content", departmentColor: "bg-blue-100 text-blue-700",
    persona: "Multi-channel copy generation with brand voice learning and iterative refinement",
    stats: { tasks: 89, avgQuality: 8.4, toolsConnected: 2 },
    tools: [
      { id: "openai", name: "GPT-4o", icon: "🧠", connected: true, setupUrl: "https://platform.openai.com", docsUrl: "https://platform.openai.com/docs", fieldLabel: "API Key" },
      { id: "brand_memory", name: "Brand Memory", icon: "📚", connected: true, fieldLabel: "Qdrant URL" },
    ],
    capabilities: [
      { id: "linkedin_post", title: "LinkedIn Post", description: "Professional LinkedIn posts with engagement-optimized structure", steps: s("Brief", "Research", "Draft", "Review", "Polish"), tools: ["GPT-4o", "Brand Memory"] },
      { id: "email_sequence", title: "Email Sequence", description: "Multi-touch email nurture sequences with personalization", steps: s("Brief", "Strategy", "Draft Emails", "Review Each", "Finalize"), tools: ["GPT-4o"] },
      { id: "blog_article", title: "Blog Article", description: "Long-form SEO-optimized blog content with structured headers", steps: s("Brief", "Outline", "Draft", "SEO Pass", "Review"), tools: ["GPT-4o", "Brand Memory"] },
      { id: "ad_copy", title: "Ad Copy Variants", description: "Short-form ad copy with A/B messaging variants", steps: s("Brief", "Audience Analysis", "Draft Variants", "Score", "Select"), tools: ["GPT-4o"] },
    ],
    recentTasks: [
      { id: "ct1", title: "LinkedIn Thought Leadership Post", status: "complete", time_ago: "1 hour ago", iterations: 2, score: 9.0, prompt: "Write a thought leadership post about AI in marketing for our CEO's LinkedIn profile. Professional tone, include a clear CTA to our whitepaper.", tools: ["GPT-4o", "Brand Memory"], output_url: "/artifacts" },
      { id: "ct2", title: "Welcome Email Sequence (3 emails)", status: "complete", time_ago: "4 hours ago", iterations: 3, score: 8.5, prompt: "Create a 3-email welcome sequence for new trial users. Emails: Day 0 (welcome), Day 3 (feature highlight), Day 7 (conversion push).", tools: ["GPT-4o"], output_url: "/artifacts" },
      { id: "ct3", title: "Product Update Blog Post", status: "in_progress", time_ago: "6 hours ago", iterations: 1, score: null, prompt: "Write a 1200-word blog post about our new analytics dashboard release.", tools: ["GPT-4o", "Brand Memory"] },
    ],
  },

  seo: {
    name: "seo", label: "SEO Agent", title: "SEO Content Specialist", avatar: "🔎",
    department: "Content", departmentColor: "bg-blue-100 text-blue-700",
    persona: "Keyword research, on-page optimization, and content scoring for search performance",
    stats: { tasks: 34, avgQuality: 8.8, toolsConnected: 2 },
    tools: [
      { id: "semrush", name: "SEMrush", icon: "📈", connected: false, docsUrl: "https://developer.semrush.com", fieldLabel: "API Key" },
      { id: "gsc", name: "Google Search Console", icon: "🔍", connected: false, docsUrl: "https://developers.google.com/webmaster-tools", fieldLabel: "MCP URL", fieldType: "mcp" as const },
      { id: "openai_seo", name: "GPT-4o", icon: "🧠", connected: true, setupUrl: "https://platform.openai.com", fieldLabel: "API Key" },
    ],
    capabilities: [
      { id: "keyword_strategy", title: "Keyword Strategy", description: "Research and prioritize target keywords for content planning", steps: s("Brief", "Keyword Research", "Competition Analysis", "Prioritize", "Deliver Report"), tools: ["SEMrush", "GPT-4o"] },
      { id: "content_optimization", title: "Content Optimization", description: "Optimize existing content for search with meta tags and structure", steps: s("Input Content", "Analyze", "Optimize Elements", "Score", "Deliver"), tools: ["GPT-4o"] },
      { id: "seo_audit", title: "SEO Content Audit", description: "Audit content pages for SEO best practices and quick wins", steps: s("Page URL", "Crawl", "Score Factors", "Recommendations", "Report"), tools: ["SEMrush", "GPT-4o"] },
    ],
    recentTasks: [
      { id: "st1", title: "Q2 Keyword Strategy", status: "complete", time_ago: "3 hours ago", iterations: 1, score: 9.2, prompt: "Research top keywords for AI marketing automation in the B2B SaaS space. Focus on long-tail keywords with medium competition.", tools: ["GPT-4o"], output_url: "/artifacts" },
      { id: "st2", title: "Blog Post SEO Optimization", status: "complete", time_ago: "1 day ago", iterations: 2, score: 8.5, prompt: "Optimize our 'AI Analytics Dashboard' blog post for search. Generate title tags, meta descriptions, H2 structure, and internal linking recommendations.", tools: ["GPT-4o"], output_url: "/artifacts" },
    ],
  },

  pm: {
    name: "pm", label: "Project Manager", title: "Project Manager", avatar: "📋",
    department: "Operations", departmentColor: "bg-gray-100 text-gray-700",
    persona: "Brief decomposition, cross-agent coordination, and delivery tracking",
    stats: { tasks: 56, avgQuality: 8.2, toolsConnected: 3 },
    tools: [
      { id: "jira", name: "Jira", icon: "🎫", connected: true, setupUrl: "https://id.atlassian.com", docsUrl: "https://developer.atlassian.com/cloud/jira/platform/rest/v3", fieldLabel: "API Token" },
      { id: "confluence", name: "Confluence", icon: "📄", connected: true, setupUrl: "https://id.atlassian.com", docsUrl: "https://developer.atlassian.com/cloud/confluence/rest/v2", fieldLabel: "API Token" },
      { id: "github", name: "GitHub", icon: "🐙", connected: false, docsUrl: "https://docs.github.com/en/rest", fieldLabel: "Personal Access Token" },
    ],
    capabilities: [
      { id: "brief_decompose", title: "Brief Decomposition", description: "Break complex briefs into scoped tasks for each agent", steps: s("Brief", "Analyze Requirements", "Decompose", "Assign Agents", "Deliver Plan"), tools: ["GPT-4o"] },
      { id: "create_ticket", title: "Jira Ticket", description: "Create structured Jira tickets from task descriptions", steps: s("Brief", "Format", "Create Ticket", "Confirm"), tools: ["Jira"] },
      { id: "publish_page", title: "Confluence Page", description: "Publish content to Confluence with proper formatting", steps: s("Content", "Format HTML", "Publish", "Share Link"), tools: ["Confluence"] },
    ],
    recentTasks: [
      { id: "pt1", title: "Q2 Campaign Brief Decomposition", status: "complete", time_ago: "2 hours ago", iterations: 1, score: 8.0, prompt: "Decompose the Q2 product launch campaign into tasks for copywriter, designer, and SEO agents.", tools: ["GPT-4o"], output_url: "/artifacts" },
    ],
  },

  competitive_intel: {
    name: "competitive_intel", label: "Competitive Analyst", title: "Competitive Analyst", avatar: "🕵️",
    department: "Strategy", departmentColor: "bg-purple-100 text-purple-700",
    persona: "Competitor mapping, market gap analysis, and positioning insights",
    stats: { tasks: 18, avgQuality: 8.9, toolsConnected: 2 },
    tools: [
      { id: "semrush_ci", name: "SEMrush", icon: "📈", connected: false, docsUrl: "https://developer.semrush.com", fieldLabel: "API Key" },
      { id: "openai_ci", name: "GPT-4o", icon: "🧠", connected: true, fieldLabel: "API Key" },
    ],
    capabilities: [
      { id: "competitor_analysis", title: "Competitor Analysis", description: "Deep-dive analysis of 3-5 competitors with positioning angles", steps: s("Brief", "Identify Competitors", "Analyze Positioning", "Find Gaps", "Report"), tools: ["SEMrush", "GPT-4o"] },
      { id: "market_gaps", title: "Market Gap Finder", description: "Identify underserved opportunities in your market", steps: s("Market Brief", "Research", "Gap Analysis", "Opportunities", "Recommendations"), tools: ["GPT-4o"] },
    ],
    recentTasks: [
      { id: "ci1", title: "AI Marketing Tools Landscape", status: "complete", time_ago: "1 day ago", iterations: 1, score: 9.0, prompt: "Analyze the competitive landscape for AI marketing automation tools. Focus on HubSpot, Jasper, Copy.ai, and Writer.", tools: ["GPT-4o"], output_url: "/artifacts" },
    ],
  },

  product_marketing: {
    name: "product_marketing", label: "Product Marketer", title: "Product Marketer", avatar: "🚀",
    department: "Strategy", departmentColor: "bg-purple-100 text-purple-700",
    persona: "Value propositions, messaging matrices, and go-to-market narrative development",
    stats: { tasks: 22, avgQuality: 8.7, toolsConnected: 1 },
    tools: [
      { id: "openai_pm", name: "GPT-4o", icon: "🧠", connected: true, fieldLabel: "API Key" },
    ],
    capabilities: [
      { id: "positioning", title: "Positioning Statement", description: "Craft a clear positioning statement for your product or feature", steps: s("Brief", "Market Context", "Draft Statement", "Refine", "Finalize"), tools: ["GPT-4o"] },
      { id: "messaging_matrix", title: "Messaging Matrix", description: "Audience × value prop × proof point matrix for campaigns", steps: s("Brief", "Identify Audiences", "Map Value Props", "Add Proof Points", "Deliver"), tools: ["GPT-4o"] },
      { id: "launch_narrative", title: "Launch Narrative", description: "Compelling product launch story with channel recommendations", steps: s("Brief", "Research", "Craft Narrative", "Channel Strategy", "Review"), tools: ["GPT-4o"] },
    ],
    recentTasks: [
      { id: "pmk1", title: "Analytics Dashboard Positioning", status: "complete", time_ago: "4 hours ago", iterations: 2, score: 8.8, prompt: "Create positioning statement for our new AI analytics dashboard targeting VP of Marketing personas.", tools: ["GPT-4o"], output_url: "/artifacts" },
    ],
  },

  review: {
    name: "review", label: "Quality Reviewer", title: "Copy Editor", avatar: "📑",
    department: "Content", departmentColor: "bg-blue-100 text-blue-700",
    persona: "Multi-criteria quality scoring with actor-critic review loops",
    stats: { tasks: 72, avgQuality: 8.1, toolsConnected: 1 },
    tools: [
      { id: "openai_rv", name: "GPT-4o-mini", icon: "🧠", connected: true, fieldLabel: "API Key" },
    ],
    capabilities: [
      { id: "content_review", title: "Content Review", description: "Score content on brand fit, clarity, and CTA strength with detailed feedback", steps: s("Input Content", "Actor-Critic Loop", "Score", "Feedback", "Verdict"), tools: ["GPT-4o-mini"] },
      { id: "brand_check", title: "Brand Voice Check", description: "Verify content alignment with brand guidelines and voice", steps: s("Input Content", "Compare Brand", "Score Alignment", "Suggestions"), tools: ["GPT-4o-mini", "Brand Memory"] },
    ],
    recentTasks: [
      { id: "rv1", title: "LinkedIn Post Review — Q2 Launch", status: "complete", time_ago: "2 hours ago", iterations: 2, score: 8.5, prompt: "Review the LinkedIn post for Q2 launch. Score on brand_fit, clarity, cta_strength. Provide actionable feedback.", tools: ["GPT-4o-mini"], output_url: "/artifacts" },
    ],
  },

  research: {
    name: "research", label: "Research Analyst", title: "Market Researcher", avatar: "📊",
    department: "Strategy", departmentColor: "bg-purple-100 text-purple-700",
    persona: "Knowledge base search, brain queries, and context grounding for other agents",
    stats: { tasks: 41, avgQuality: 8.3, toolsConnected: 2 },
    tools: [
      { id: "qdrant", name: "Knowledge Base", icon: "📚", connected: true, fieldLabel: "Qdrant URL" },
      { id: "brain", name: "Agency Brain", icon: "🧠", connected: true, fieldLabel: "Qdrant URL" },
    ],
    capabilities: [
      { id: "market_research", title: "Market Research", description: "Deep research queries using knowledge base and agency brain", steps: s("Query", "Search KB", "Search Brain", "Synthesize", "Report"), tools: ["Knowledge Base", "Brain"] },
      { id: "context_brief", title: "Context Brief", description: "Generate context briefs to feed other agents before tasks", steps: s("Topic", "Gather Sources", "Summarize", "Deliver Context"), tools: ["Knowledge Base", "Brain"] },
    ],
    recentTasks: [
      { id: "rs1", title: "AI Marketing Trends Q2 2026", status: "complete", time_ago: "6 hours ago", iterations: 1, score: 8.7, prompt: "Research latest trends in AI-powered marketing for Q2 2026. Include industry shifts, tool adoption, and budget allocation data.", tools: ["Knowledge Base", "Brain"], output_url: "/artifacts" },
    ],
  },
};

/* Helper: build workflow steps for demo (all pending) */
function s(...labels: string[]): WorkflowStep[] {
  return labels.map((label) => ({ label, state: "pending" as const }));
}

/* ═══════════════════════════════════════════════════════════════════
   EXECUTION VIEW  — per-skill, per-platform, real backend execution
   ═══════════════════════════════════════════════════════════════════ */

type ExecPhase = "loading" | "questions" | "planning" | "running" | "iteration" | "done" | "error";

/** Shape returned by GET /future/agents/{name}/activities/{id} */
type ActivityDef = {
  id: string;
  agent: string;
  title: string;
  description: string;
  input_schema: { id: string; label: string; type: string; options?: string[]; hint?: string; required?: boolean }[];
  workflow: string[];
  tools: string[];
  output_type: string;
};

/** Shape returned by GET /design/config/tools */
type ToolConfigEntry = { skill_id: string; primary_tool: string; backup_tool: string; enabled: boolean };
/** Shape returned by GET /design/config/rules */
type DesignRules = {
  max_iterations: number; default_quality: string; auto_review: boolean;
  auto_approve_min_score: number; style_prompt_prefix: string;
};
/** Shape returned by GET /design/config/presets */
type PresetEntry = {
  skill_id: string; platform: string; label: string;
  width: number; height: number; aspect_ratio: string;
  resolution: string; format: string;
};

/** Shape returned by POST .../execute */
type ExecuteResult = {
  ok: boolean; image_url: string; download_url: string;
  provider: string; model: string; revised_prompt: string;
  aspect_ratio: string; resolution: string; mime_type: string;
  skill_id: string; platform: string;
};

function ExecutionView({
  agent, capabilityId, onBack,
}: { agent: AgentProfile; capabilityId: string; onBack: () => void }) {
  const { online } = useBackend();
  const [phase, setPhase] = useState<ExecPhase>("loading");
  const [narration, setNarration] = useState<NarrationEntry[]>([]);
  const idRef = useRef(0);

  // Loaded from backend
  const [activity, setActivity] = useState<ActivityDef | null>(null);
  const [toolConfigs, setToolConfigs] = useState<ToolConfigEntry[]>([]);
  const [rules, setRules] = useState<DesignRules | null>(null);
  const [presets, setPresets] = useState<PresetEntry[]>([]);

  // Execution state
  const [answers, setAnswers] = useState<Record<string, string | string[]>>({});
  const [promptText, setPromptText] = useState("");
  const [iterationCount, setIterationCount] = useState(0);
  const [lastResult, setLastResult] = useState<ExecuteResult | null>(null);
  const [errorMsg, setErrorMsg] = useState("");

  /* ── Load activity definition + engine config on mount ── */
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        // Try backend first; if offline, build from DEMO_AGENTS capabilities
        if (online) {
          const [actData, toolsData, rulesData, presetsData] = await Promise.all([
            futureAgents.activity(agent.name, capabilityId),
            designConfig.getTools().catch(() => []),
            designConfig.getRules().catch(() => null),
            designConfig.getPresets(capabilityId).catch(() => []),
          ]);
          if (cancelled) return;
          setActivity(actData);
          setToolConfigs(toolsData);
          setRules(rulesData);
          setPresets(presetsData);
        } else {
          // Offline fallback: build ActivityDef from DEMO_AGENTS
          const cap = agent.capabilities.find((c) => c.id === capabilityId);
          if (cap) {
            // Use the hardcoded capabilities as a minimal ActivityDef
            setActivity({
              id: cap.id,
              agent: agent.name,
              title: cap.title,
              description: cap.description,
              input_schema: buildOfflineSchema(cap.id),
              workflow: cap.steps.map((s) => s.label),
              tools: cap.tools,
              output_type: "image",
            });
          }
        }
        if (!cancelled) setPhase("questions");
      } catch (err) {
        if (!cancelled) {
          // Fall back to offline schema on API error
          const cap = agent.capabilities.find((c) => c.id === capabilityId);
          if (cap) {
            setActivity({
              id: cap.id,
              agent: agent.name,
              title: cap.title,
              description: cap.description,
              input_schema: buildOfflineSchema(cap.id),
              workflow: cap.steps.map((s) => s.label),
              tools: cap.tools,
              output_type: "image",
            });
          }
          setPhase("questions");
        }
      }
    }
    load();
    return () => { cancelled = true; };
  }, [agent, capabilityId, online]);

  /* ── Derive per-skill questions from activity.input_schema ── */
  const questions: AgentQuestion[] = useMemo(() => {
    if (!activity) return [];
    return activity.input_schema.map((f) => ({
      id: f.id,
      label: f.label,
      type: f.type === "multiselect" ? "multiselect" as const : f.type === "select" ? "select" as const : "text" as const,
      options: f.options,
      hint: f.hint,
      required: f.required,
    }));
  }, [activity]);

  /* ── Derive per-skill plan from workflow + engine config ── */
  const plan: PlanStep[] = useMemo(() => {
    if (!activity) return [];
    const tc = toolConfigs.find((t) => t.skill_id === capabilityId);
    const primaryTool = tc?.primary_tool ?? activity.tools[0] ?? "";
    const selectedPreset = presets[0]; // first matching preset

    return activity.workflow.map((stepLabel, i) => {
      const isGenerate = /generate|create|image/i.test(stepLabel);
      const isReview = /review|check/i.test(stepLabel);
      return {
        id: `p${i}`,
        label: stepLabel,
        tool: isGenerate ? primaryTool : isReview ? "Quality Reviewer" : undefined,
        estimated: isGenerate ? "~15-30s" : isReview ? "~5s" : undefined,
        status: "pending" as const,
      };
    });
  }, [activity, toolConfigs, presets, capabilityId]);

  /* ── Plan summary based on skill + answers ── */
  const planSummary = useMemo(() => {
    if (!activity) return "";
    const tc = toolConfigs.find((t) => t.skill_id === capabilityId);
    const tool = tc?.primary_tool ?? activity.tools[0] ?? "AI";
    const selectedPreset = presets[0];
    const dims = selectedPreset ? `${selectedPreset.width}×${selectedPreset.height}` : "";
    const platform = (answers.platform as string) || "";

    return `I'll create a ${activity.title.toLowerCase()}${platform ? ` for ${platform}` : ""} using ${tool}${dims ? ` at ${dims}px` : ""}${rules?.style_prompt_prefix ? ". Your brand style rules will be applied." : ""}. I'll iterate until you're satisfied (max ${rules?.max_iterations ?? 5} iterations).`;
  }, [activity, toolConfigs, presets, answers, rules, capabilityId]);

  const addNarration = useCallback((type: NarrationEntry["type"], text: string, detail?: string) => {
    idRef.current += 1;
    setNarration((n) => [...n, { id: String(idRef.current), type, text, detail, timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) }]);
  }, []);

  /* ── Execute via real API ── */
  const executeTask = useCallback(async (overridePrompt?: string) => {
    if (!activity) return;
    setPhase("running");

    const tc = toolConfigs.find((t) => t.skill_id === capabilityId);
    const toolName = tc?.primary_tool ?? activity.tools[0] ?? "AI";
    const platform = (answers.platform as string) || (answers.campaign as string) || "";
    const selectedPreset = presets[0];

    // Build prompt from answers + promptText
    const promptParts: string[] = [];
    if (overridePrompt) {
      promptParts.push(overridePrompt);
    } else if (promptText) {
      promptParts.push(promptText);
    }
    // Add all text-type answers as context
    for (const [key, val] of Object.entries(answers)) {
      if (typeof val === "string" && val.trim() && key !== "platform") {
        const field = activity.input_schema.find((f) => f.id === key);
        promptParts.push(`${field?.label ?? key}: ${val}`);
      } else if (Array.isArray(val) && val.length > 0) {
        const field = activity.input_schema.find((f) => f.id === key);
        promptParts.push(`${field?.label ?? key}: ${val.join(", ")}`);
      }
    }
    const fullPrompt = promptParts.join(". ");

    addNarration("thinking", `Analyzing your brief for ${activity.title}...`,
      selectedPreset ? `Target: ${selectedPreset.width}×${selectedPreset.height}px (${selectedPreset.aspect_ratio})` : undefined);

    if (!online) {
      // Offline: simulate with realistic per-skill narration
      setTimeout(() => addNarration("tool", `Would call ${toolName}...`, "Backend offline — showing preview mode"), 600);
      setTimeout(() => {
        addNarration("milestone", "Preview ready (connect backend for real generation)");
        setIterationCount((c) => c + 1);
        setLastResult(null);
        setPhase("iteration");
      }, 1200);
      return;
    }

    try {
      addNarration("tool", `Calling ${toolName}...`,
        selectedPreset ? `${selectedPreset.resolution || "1K"} resolution, ${selectedPreset.aspect_ratio} aspect ratio` : undefined);

      const result: ExecuteResult = await futureAgents.execute(agent.name, capabilityId, {
        prompt: fullPrompt,
        platform,
        options: {
          ...answers,
          style: answers.style,
          iteration: iterationCount + 1,
        },
      });

      addNarration("observation", `Image generated via ${result.provider || toolName}`,
        result.revised_prompt ? `Revised prompt: "${result.revised_prompt.slice(0, 100)}..."` : undefined);
      addNarration("milestone", `Iteration ${iterationCount + 1} ready for your review!`);

      setLastResult(result);
      setIterationCount((c) => c + 1);
      setPhase("iteration");
    } catch (err: any) {
      const msg = err?.userMessage || err?.message || "Execution failed";
      addNarration("observation", `Error: ${msg}`);
      setErrorMsg(msg);
      setPhase("error");
    }
  }, [activity, answers, promptText, toolConfigs, presets, capabilityId, agent.name, online, iterationCount, addNarration]);

  /* ── Retry with same params ── */
  const handleRetry = useCallback(() => {
    const maxIter = rules?.max_iterations ?? 5;
    if (iterationCount >= maxIter) {
      addNarration("observation", `Max iterations (${maxIter}) reached. Approve or adjust.`);
      return;
    }
    addNarration("thinking", "Generating a different angle with the same parameters...");
    executeTask();
  }, [executeTask, iterationCount, rules, addNarration]);

  /* ── Adjust with feedback ── */
  const handleAdjust = useCallback((feedback: string) => {
    const maxIter = rules?.max_iterations ?? 5;
    if (iterationCount >= maxIter) {
      addNarration("observation", `Max iterations (${maxIter}) reached.`);
      return;
    }
    addNarration("thinking", `Adjusting based on your feedback: "${feedback}"`);
    const base = promptText || Object.values(answers).filter(Boolean).join(". ");
    executeTask(`${base}. Adjustment: ${feedback}`);
  }, [executeTask, promptText, answers, iterationCount, rules, addNarration]);

  /* ── Approve ── */
  const handleApprove = useCallback(() => {
    addNarration("milestone", "Approved! Saving to artifacts and brand memory.");
    setPhase("done");
  }, [addNarration]);

  /* ── Handle question answers ── */
  const handleQuestionsSubmit = useCallback((ans: Record<string, string | string[]>) => {
    setAnswers(ans);
    setPhase("planning");
  }, []);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-200 bg-white shrink-0">
        <button onClick={onBack} className="text-gray-400 hover:text-gray-600 transition-colors">
          <ArrowLeft className="w-4 h-4" />
        </button>
        <span className="text-2xl">{agent.avatar}</span>
        <div>
          <p className="text-sm font-semibold text-gray-800">
            {agent.label} — {activity?.title ?? "Working"}
          </p>
          <p className="text-[11px] text-gray-500">
            {phase === "loading" ? "Loading skill definition..." :
             phase === "questions" ? "Gathering requirements" :
             phase === "planning" ? "Review the plan" :
             phase === "running" ? "Generating..." :
             phase === "iteration" ? `Iteration ${iterationCount} — review output` :
             phase === "error" ? "Something went wrong" :
             "Task complete"}
          </p>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-3xl mx-auto space-y-4">
          {phase === "loading" && (
            <div className="flex items-center justify-center py-16">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
            </div>
          )}

          {phase === "questions" && (
            <AgentQuestionForm
              agentName={agent.label}
              avatar={agent.avatar}
              preamble={activity ? `Let me gather details for "${activity.title}".` : "Before I start, let me understand what you need."}
              questions={questions}
              onSubmit={handleQuestionsSubmit}
            />
          )}

          {phase === "planning" && (
            <AgentPlanCard
              agentName={agent.label}
              avatar={agent.avatar}
              summary={planSummary}
              estimatedTime={`~${Math.max(15, plan.length * 10)}s`}
              steps={plan}
              onApprove={() => executeTask()}
              onModify={(fb) => { setPromptText(fb); executeTask(fb); }}
              onCancel={onBack}
            />
          )}

          {(phase === "running" || phase === "iteration") && (
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
              {/* Narration — left */}
              <div className="lg:col-span-2">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Agent Activity</p>
                <AgentNarration entries={narration} streaming={phase === "running"} />
              </div>

              {/* Preview — right */}
              <div className="lg:col-span-3">
                {phase === "iteration" && (
                  <IterationPreview
                    iteration={iterationCount}
                    output={lastResult?.revised_prompt ?? ""}
                    imageUrl={lastResult?.image_url || `https://placehold.co/800x800/e2e8f0/64748b?text=${encodeURIComponent(activity?.title ?? "Preview")}+%28offline%29`}
                    agentCommentary={
                      lastResult
                        ? `Generated via ${lastResult.provider}${lastResult.aspect_ratio ? ` at ${lastResult.aspect_ratio}` : ""}.`
                        : `Connect backend to generate real ${activity?.title?.toLowerCase() ?? "outputs"}.`
                    }
                    onProceed={handleApprove}
                    onRetry={handleRetry}
                    onAdjust={handleAdjust}
                  />
                )}
              </div>
            </div>
          )}

          {phase === "error" && (
            <div className="text-center py-12">
              <span className="text-5xl mb-4 block">⚠️</span>
              <h3 className="text-lg font-semibold text-gray-800 mb-2">Execution Failed</h3>
              <p className="text-sm text-gray-500 mb-4">{errorMsg}</p>
              <div className="flex items-center justify-center gap-3">
                <button
                  onClick={() => { setErrorMsg(""); executeTask(); }}
                  className="text-sm font-medium px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Retry
                </button>
                <button
                  onClick={onBack}
                  className="text-sm font-medium text-gray-600 hover:text-gray-700"
                >
                  ← Back to workspace
                </button>
              </div>
            </div>
          )}

          {phase === "done" && (
            <div className="text-center py-12">
              <span className="text-5xl mb-4 block">✅</span>
              <h3 className="text-lg font-semibold text-gray-800 mb-2">Task Complete</h3>
              <p className="text-sm text-gray-500 mb-6">
                {activity?.title} saved to artifacts and brand memory.
                {lastResult?.download_url && (
                  <a href={lastResult.download_url} target="_blank" rel="noopener noreferrer" className="ml-2 text-blue-600 hover:underline inline-flex items-center gap-1">
                    Download <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </p>
              <button
                onClick={onBack}
                className="text-sm font-medium text-blue-600 hover:text-blue-700"
              >
                ← Back to workspace
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Command bar (feedback mode) */}
      {(phase === "running" || phase === "iteration") && (
        <CommandBar
          tools={agent.tools.filter((t) => t.connected).map((t) => ({ id: t.id, label: t.name, icon: t.icon }))}
          placeholder={`Feedback for ${activity?.title ?? "this task"}...`}
          onSubmit={(text) => {
            handleAdjust(text);
          }}
        />
      )}
    </div>
  );
}

/**
 * Offline fallback: build per-skill input schemas when backend isn't available.
 * This mirrors activities.yaml but lives in the frontend for offline UX.
 */
function buildOfflineSchema(capabilityId: string): ActivityDef["input_schema"] {
  const schemas: Record<string, ActivityDef["input_schema"]> = {
    social_visual: [
      { id: "platform", label: "Which platform?", type: "select", options: ["LinkedIn", "Instagram", "Twitter", "Facebook"], required: true },
      { id: "style", label: "Visual style?", type: "select", options: ["Modern Minimalist", "Bold & Colorful", "Corporate Clean", "Playful", "Dark & Premium"] },
      { id: "details", label: "Specific elements?", type: "text", hint: "Brand colors, taglines, imagery…" },
    ],
    email_header: [
      { id: "campaign", label: "Campaign name or theme?", type: "text", required: true },
      { id: "width", label: "Header width?", type: "select", options: ["600px", "700px", "100%"] },
    ],
    brand_asset: [
      { id: "asset_types", label: "Which assets?", type: "multiselect", options: ["Logo", "Banner", "Icon Set", "Social Kit", "Favicon"], required: true },
      { id: "brand_notes", label: "Brand guidelines or notes?", type: "text" },
    ],
    ad_creative: [
      { id: "platform", label: "Ad platform?", type: "select", options: ["Facebook Ads", "Google Display", "LinkedIn Ads", "Instagram Ads"], required: true },
      { id: "variant_count", label: "How many variants?", type: "select", options: ["2", "3", "4"] },
    ],
    presentation_slide: [
      { id: "topic", label: "Slide topic or title?", type: "text", required: true },
      { id: "layout", label: "Layout style?", type: "select", options: ["Title Slide", "Content + Image", "Data Visualization", "Quote", "Comparison"] },
    ],
    // Copy agent
    linkedin_post: [
      { id: "topic", label: "Post topic?", type: "text", required: true },
      { id: "tone", label: "Tone?", type: "select", options: ["Professional", "Conversational", "Thought Leader", "Personal Story"] },
      { id: "cta", label: "Call to action?", type: "text", hint: "What should readers do?" },
    ],
    email_sequence: [
      { id: "goal", label: "Sequence goal?", type: "select", options: ["Welcome/Onboarding", "Nurture", "Re-engagement", "Product Launch", "Event Follow-up"], required: true },
      { id: "email_count", label: "Number of emails?", type: "select", options: ["3", "5", "7"] },
      { id: "audience", label: "Target audience?", type: "text" },
    ],
    blog_article: [
      { id: "topic", label: "Article topic?", type: "text", required: true },
      { id: "word_count", label: "Target length?", type: "select", options: ["600 words", "1200 words", "2000 words"] },
      { id: "keywords", label: "Target keywords?", type: "text", hint: "Comma-separated" },
    ],
    ad_copy: [
      { id: "platform", label: "Ad platform?", type: "select", options: ["Google Ads", "Facebook", "LinkedIn", "Twitter"], required: true },
      { id: "product", label: "Product or feature?", type: "text", required: true },
      { id: "variant_count", label: "How many variants?", type: "select", options: ["2", "3", "5"] },
    ],
    // SEO agent
    keyword_strategy: [
      { id: "topic", label: "Topic or niche?", type: "text", required: true },
      { id: "market", label: "Target market?", type: "select", options: ["US", "UK", "EU", "Global", "APAC"] },
      { id: "intent", label: "Search intent?", type: "multiselect", options: ["Informational", "Transactional", "Navigational", "Commercial"] },
    ],
    content_optimization: [
      { id: "content", label: "Paste content or URL", type: "text", required: true },
      { id: "target_keyword", label: "Primary target keyword?", type: "text" },
    ],
    seo_audit: [
      { id: "url", label: "Page URL to audit", type: "text", required: true },
    ],
    // PM agent
    brief_decompose: [
      { id: "brief", label: "Paste the campaign brief", type: "text", required: true },
      { id: "agents", label: "Which agents should be involved?", type: "multiselect", options: ["Copywriter", "Designer", "SEO", "Product Marketing"] },
    ],
    // Competitive Intel
    competitor_analysis: [
      { id: "competitors", label: "Competitor names (comma-separated)", type: "text", required: true },
      { id: "focus", label: "Analysis focus?", type: "select", options: ["Positioning", "Pricing", "Content Strategy", "Product Features", "Full Analysis"] },
    ],
    market_gaps: [
      { id: "market", label: "Describe your market", type: "text", required: true },
    ],
    // Product Marketing
    positioning: [
      { id: "product", label: "Product or feature name?", type: "text", required: true },
      { id: "audience", label: "Target persona?", type: "text", hint: "e.g. VP of Marketing" },
    ],
    messaging_matrix: [
      { id: "product", label: "Product or campaign?", type: "text", required: true },
      { id: "audiences", label: "Target audiences?", type: "multiselect", options: ["C-Suite", "VP Marketing", "Marketing Manager", "Developer", "End User"] },
    ],
    launch_narrative: [
      { id: "product", label: "What are you launching?", type: "text", required: true },
      { id: "channels", label: "Distribution channels?", type: "multiselect", options: ["Blog", "Email", "Social Media", "Product Hunt", "Press Release"] },
    ],
    // Review agent
    content_review: [
      { id: "content", label: "Paste the content to review", type: "text", required: true },
      { id: "criteria", label: "Review criteria?", type: "multiselect", options: ["Brand Fit", "Clarity", "CTA Strength", "Grammar", "Tone"] },
    ],
    brand_check: [
      { id: "content", label: "Paste content to check against brand", type: "text", required: true },
    ],
    // Research agent
    market_research: [
      { id: "query", label: "Research question?", type: "text", required: true },
    ],
    context_brief: [
      { id: "topic", label: "Topic for context brief?", type: "text", required: true },
    ],
  };
  return schemas[capabilityId] ?? [{ id: "prompt", label: "What do you need?", type: "text", required: true }];
}

/* ═══════════════════════════════════════════════════════════════════
   MAIN WORKSPACE PAGE
   ═══════════════════════════════════════════════════════════════════ */

export default function AgentWorkspacePage() {
  const params = useParams();
  const agentName = typeof params.name === "string" ? params.name : (params.name?.[0] ?? "design");
  const { online } = useBackend();

  const [executing, setExecuting] = useState<string | null>(null);

  const agent = DEMO_AGENTS[agentName] || DEMO_AGENTS.design;
  const toolOptions: ToolOption[] = agent.tools
    .filter((t) => t.connected)
    .map((t) => ({ id: t.id, label: t.name, icon: t.icon }));

  /* ── Execution View ─────────────────────────────────────────── */
  if (executing) {
    return <ExecutionView agent={agent} capabilityId={executing} onBack={() => setExecuting(null)} />;
  }

  /* ── Workspace View ─────────────────────────────────────────── */
  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto px-6 py-6 space-y-8">
          {!online && (
            <DemoBanner
              compact
              feature={agent.label}
              steps={["Start the backend", "Connect agent tools", "Run a task"]}
            />
          )}

          {/* ── ZONE 1: Identity Bar ──────────────────────────── */}
          <div className="flex items-center gap-4">
            <span className="text-4xl">{agent.avatar}</span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2.5 flex-wrap">
                <h1 className="text-xl font-bold text-gray-800">{agent.label}</h1>
                <span className="text-xs text-gray-500">•</span>
                <span className="text-sm text-gray-500">{agent.title}</span>
                <span className={clsx("text-[10px] font-medium px-2 py-0.5 rounded-full", agent.departmentColor)}>
                  {agent.department}
                </span>
              </div>
              <p className="text-sm text-gray-500 mt-1">{agent.persona}</p>
              <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                <span><strong className="text-gray-700">{agent.stats.tasks}</strong> tasks completed</span>
                <span className="text-gray-300">•</span>
                <span><strong className="text-gray-700">{agent.stats.avgQuality}</strong> avg quality</span>
                <span className="text-gray-300">•</span>
                <span><strong className="text-gray-700">{agent.stats.toolsConnected}</strong> tools connected</span>
              </div>
            </div>
            {agentName === "design" && (
              <a
                href="/future/agent/design/config"
                className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-medium rounded-lg transition-colors shrink-0"
              >
                <Settings2 className="w-3.5 h-3.5" />
                Configure Engine
              </a>
            )}
          </div>

          {/* ── ZONE 2: Toolbox ───────────────────────────────── */}
          <section>
            <div className="flex items-center gap-2 mb-3">
              <h2 className="text-sm font-semibold text-gray-700">Connected Tools</h2>
              <span className="text-[10px] font-bold bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded-full">
                {agent.tools.filter((t) => t.connected).length}/{agent.tools.length}
              </span>
            </div>
            <div className="flex gap-3 overflow-x-auto pb-2 -mx-1 px-1">
              {agent.tools.map((tool) => (
                <ToolCard
                  key={tool.id}
                  name={tool.name}
                  icon={tool.icon}
                  connected={tool.connected}
                  setupUrl={tool.setupUrl}
                  docsUrl={tool.docsUrl}
                  fieldLabel={tool.fieldLabel}
                  fieldType={tool.fieldType}
                  onConnect={async () => true}
                />
              ))}
            </div>
          </section>

          {/* ── ZONE 3: Skills (What I Can Do) ──────────────── */}
          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-gray-700">What I Can Do</h2>
              {agentName === "design" && (
                <p className="text-[11px] text-gray-400">
                  Teams: <code className="bg-gray-100 px-1 py-0.5 rounded text-[10px]">@Zima /socialmedia /prompt ...</code>
                </p>
              )}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {agent.capabilities.map((cap) => (
                <CapabilityCard
                  key={cap.id}
                  capability={cap}
                  onStart={(capId) => setExecuting(capId)}
                />
              ))}
            </div>
          </section>

          {/* ── ZONE 4: Recent Work ───────────────────────────── */}
          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-gray-700">Recent Work</h2>
              <button className="text-[11px] font-medium text-blue-600 hover:text-blue-700">View All →</button>
            </div>
            <div className="space-y-3">
              {agent.recentTasks.map((task) => (
                <TaskRow key={task.id} task={task} />
              ))}
            </div>
          </section>
        </div>
      </div>

      {/* ── ZONE 5: Command Bar ───────────────────────────────── */}
      <CommandBar
        tools={toolOptions}
        placeholder={
          agent.name === "design" ? "Describe the visual you need..." :
          agent.name === "copy" ? "What would you like me to write?" :
          agent.name === "seo" ? "What content should I optimize?" :
          "Describe what you need..."
        }
        onSubmit={(text) => {
          // Find best matching capability from prompt (default to first)
          const firstCap = agent.capabilities[0]?.id;
          setExecuting(firstCap ?? null);
        }}
      />
    </div>
  );
}
