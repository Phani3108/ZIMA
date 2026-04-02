"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Search, Sparkles, Target, Rocket, Share2, ChevronRight, WifiOff } from "lucide-react";
import clsx from "clsx";
import { skills } from "@/lib/api";

type Skill = {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: string;
  platforms: string[];
  prompts: { id: string; name: string; description: string }[];
};

const CATEGORY_META: Record<string, { label: string; color: string; icon: any }> = {
  foundation: { label: "Foundation", color: "bg-purple-100 text-purple-700 border-purple-200", icon: Sparkles },
  strategy: { label: "Strategy", color: "bg-amber-100 text-amber-700 border-amber-200", icon: Target },
  execution: { label: "Execution", color: "bg-blue-100 text-blue-700 border-blue-200", icon: Rocket },
  distribution: { label: "Distribution", color: "bg-green-100 text-green-700 border-green-200", icon: Share2 },
};

/* ─── Static catalog shown when backend is offline ──────────────── */

const STATIC_SKILLS: Skill[] = [
  { id: "brand-voice", name: "Brand Voice Builder", description: "Analyze existing content and establish tone, vocabulary, and style rules for consistent brand communication.", icon: "🎤", category: "foundation", platforms: ["all"], prompts: [{ id: "analyze", name: "Analyze Brand Voice", description: "Extract tone and style from sample content" }, { id: "guidelines", name: "Generate Guidelines", description: "Create a brand voice guide document" }]  },
  { id: "audience-persona", name: "Audience Persona Creator", description: "Build detailed customer personas from demographics, behavior patterns, and market research data.", icon: "👥", category: "foundation", platforms: ["all"], prompts: [{ id: "create", name: "Create Persona", description: "Generate a detailed audience persona" }] },
  { id: "content-strategy", name: "Content Strategy Planner", description: "Develop a comprehensive content calendar with topic clusters, SEO targets, and distribution channels.", icon: "📅", category: "strategy", platforms: ["blog", "social", "email"], prompts: [{ id: "plan", name: "Plan Strategy", description: "Generate a content strategy document" }, { id: "calendar", name: "Build Calendar", description: "Create a monthly content calendar" }] },
  { id: "seo-brief", name: "SEO Content Brief", description: "Generate keyword-optimized content briefs with search intent analysis, competitor gaps, and outline structure.", icon: "🔍", category: "strategy", platforms: ["blog", "web"], prompts: [{ id: "brief", name: "Generate Brief", description: "Create an SEO-optimized content brief" }] },
  { id: "blog-writer", name: "Blog Post Writer", description: "Write long-form blog posts with SEO optimization, structured headings, and engaging narrative flow.", icon: "✍️", category: "execution", platforms: ["blog"], prompts: [{ id: "draft", name: "Write Draft", description: "Generate a full blog post" }, { id: "outline", name: "Create Outline", description: "Build a structured outline" }] },
  { id: "social-copy", name: "Social Media Copy", description: "Create platform-specific social media posts with hashtags, CTAs, and engagement hooks.", icon: "📱", category: "execution", platforms: ["linkedin", "twitter", "instagram"], prompts: [{ id: "post", name: "Write Post", description: "Generate a social media post" }, { id: "thread", name: "Create Thread", description: "Build a multi-post thread" }] },
  { id: "email-campaign", name: "Email Campaign Writer", description: "Craft email sequences with subject lines, preview text, body copy, and A/B test variants.", icon: "📧", category: "execution", platforms: ["email"], prompts: [{ id: "sequence", name: "Write Sequence", description: "Generate a multi-email campaign" }, { id: "single", name: "Write Single", description: "Write one email with A/B variants" }] },
  { id: "ad-copy", name: "Ad Copy Generator", description: "Generate high-converting ad copy for Google, Meta, and LinkedIn with headline variants.", icon: "📢", category: "execution", platforms: ["google-ads", "meta", "linkedin"], prompts: [{ id: "generate", name: "Generate Ads", description: "Create ad copy with multiple variants" }] },
  { id: "social-scheduler", name: "Social Scheduler", description: "Schedule and publish content across social platforms with optimal timing suggestions.", icon: "⏰", category: "distribution", platforms: ["buffer", "linkedin"], prompts: [{ id: "schedule", name: "Schedule Posts", description: "Queue posts with optimal timing" }] },
  { id: "campaign-analytics", name: "Campaign Analytics", description: "Analyze campaign performance across channels with actionable insights and optimization recommendations.", icon: "📊", category: "distribution", platforms: ["all"], prompts: [{ id: "report", name: "Generate Report", description: "Create a performance analytics report" }] },
  { id: "competitive-intel", name: "Competitive Intelligence", description: "Monitor competitor content, messaging, and positioning to identify opportunities and gaps.", icon: "🕵️", category: "strategy", platforms: ["all"], prompts: [{ id: "analyze", name: "Analyze Competitor", description: "Deep-dive on a competitor's strategy" }] },
  { id: "product-launch", name: "Product Launch Kit", description: "Generate a complete product launch package: press release, landing page copy, email blasts, and social campaigns.", icon: "🚀", category: "execution", platforms: ["all"], prompts: [{ id: "kit", name: "Generate Launch Kit", description: "Create full product launch materials" }] },
];

export default function SkillsPage() {
  const [allSkills, setAllSkills] = useState<Skill[]>([]);
  const [filteredSkills, setFilteredSkills] = useState<Skill[]>([]);
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [backendOnline, setBackendOnline] = useState(true);

  useEffect(() => {
    skills.list().then((data) => {
      if (data && Array.isArray(data) && data.length > 0) {
        setAllSkills(data);
        setFilteredSkills(data);
      } else {
        setBackendOnline(false);
        setAllSkills(STATIC_SKILLS);
        setFilteredSkills(STATIC_SKILLS);
      }
      setLoading(false);
    }).catch(() => {
      setBackendOnline(false);
      setAllSkills(STATIC_SKILLS);
      setFilteredSkills(STATIC_SKILLS);
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    let result = allSkills;
    if (activeCategory) {
      result = result.filter((s) => s.category === activeCategory);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (s) =>
          s.name.toLowerCase().includes(q) ||
          s.description.toLowerCase().includes(q) ||
          s.prompts.some((p) => p.name.toLowerCase().includes(q))
      );
    }
    setFilteredSkills(result);
  }, [search, activeCategory, allSkills]);

  const categories = Object.entries(CATEGORY_META);

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Skills Catalog</h1>
        <p className="text-gray-500 mt-1">
          Pre-built marketing skills with AI-powered prompts. Select a skill to start a workflow.
        </p>
      </div>

      {/* Search + Filters */}
      {!backendOnline && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-5 py-3 mb-6 flex items-start gap-3">
          <WifiOff size={18} className="text-amber-600 mt-0.5 shrink-0" />
          <div>
            <h3 className="text-sm font-semibold text-amber-800">Preview Mode</h3>
            <p className="text-xs text-amber-700 mt-0.5">
              Showing the built-in skills catalog. Connect a backend to run workflows and execute prompts.
            </p>
          </div>
        </div>
      )}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search skills, prompts..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2.5 border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand"
          />
        </div>
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={() => setActiveCategory(null)}
            className={clsx(
              "px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors",
              !activeCategory ? "bg-gray-900 text-white border-gray-900" : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
            )}
          >
            All
          </button>
          {categories.map(([key, meta]) => (
            <button
              key={key}
              onClick={() => setActiveCategory(activeCategory === key ? null : key)}
              className={clsx(
                "px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors",
                activeCategory === key ? meta.color : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
              )}
            >
              {meta.label}
            </button>
          ))}
        </div>
      </div>

      {/* Skills Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="bg-white rounded-xl border p-5 animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-1/3 mb-3" />
              <div className="h-3 bg-gray-100 rounded w-full mb-2" />
              <div className="h-3 bg-gray-100 rounded w-2/3" />
            </div>
          ))}
        </div>
      ) : filteredSkills.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          No skills found{search ? ` for "${search}"` : ""}.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredSkills.map((skill) => {
            const catMeta = CATEGORY_META[skill.category];
            return (
              <Link
                key={skill.id}
                href={`/skills/${skill.id}`}
                className="group bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md hover:border-brand/30 transition-all"
              >
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <span className={clsx("text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full border", catMeta?.color)}>
                      {skill.category}
                    </span>
                  </div>
                  <ChevronRight size={14} className="text-gray-300 group-hover:text-brand transition-colors" />
                </div>

                <h3 className="font-semibold text-gray-900 mb-1">{skill.name}</h3>
                <p className="text-xs text-gray-500 line-clamp-2 mb-3">{skill.description}</p>

                <div className="flex items-center justify-between">
                  <span className="text-[11px] text-gray-400">
                    {skill.prompts.length} prompt{skill.prompts.length !== 1 ? "s" : ""}
                  </span>
                  <div className="flex gap-1">
                    {skill.platforms.slice(0, 3).map((p) => (
                      <span key={p} className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">
                        {p}
                      </span>
                    ))}
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
