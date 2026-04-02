/**
 * Static skill catalog — shown as fallback when the backend is offline.
 * Shared between /skills (list) and /skills/[id] (detail).
 */

export type StaticPrompt = {
  id: string;
  name: string;
  description: string;
  variables: string[];
  platform: string;
  output_type: string;
  example_output: string;
  agent: string;
};

export type StaticSkill = {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: string;
  platforms: string[];
  tools_used: string[];
  workflow_stages: string[];
  default_llm: string;
  fallback_llms: string[];
  prompts: StaticPrompt[];
};

export const STATIC_SKILLS: StaticSkill[] = [
  {
    id: "brand-voice",
    name: "Brand Voice Builder",
    description: "Analyze existing content and establish tone, vocabulary, and style rules for consistent brand communication.",
    icon: "🎤",
    category: "foundation",
    platforms: ["all"],
    tools_used: ["Azure OpenAI", "Brand Memory"],
    workflow_stages: ["Analyze Samples", "Extract Patterns", "Generate Guidelines", "Review"],
    default_llm: "gpt-4o",
    fallback_llms: ["gpt-4o-mini"],
    prompts: [
      { id: "analyze", name: "Analyze Brand Voice", description: "Extract tone and style from sample content", variables: ["sample_content", "brand_name"], platform: "all", output_type: "analysis", example_output: "Tone: Professional yet approachable. Vocabulary: Technical terms simplified for general audience...", agent: "strategist" },
      { id: "guidelines", name: "Generate Guidelines", description: "Create a brand voice guide document", variables: ["brand_name", "target_audience", "industry"], platform: "all", output_type: "document", example_output: "# Brand Voice Guidelines\n\n## Core Voice Attributes\n1. **Confident** — We speak with authority...", agent: "strategist" },
    ],
  },
  {
    id: "audience-persona",
    name: "Audience Persona Creator",
    description: "Build detailed customer personas from demographics, behavior patterns, and market research data.",
    icon: "👥",
    category: "foundation",
    platforms: ["all"],
    tools_used: ["Azure OpenAI", "SEMrush"],
    workflow_stages: ["Research", "Segment", "Build Persona", "Review"],
    default_llm: "gpt-4o",
    fallback_llms: ["gpt-4o-mini"],
    prompts: [
      { id: "create", name: "Create Persona", description: "Generate a detailed audience persona", variables: ["product_description", "target_market", "demographics"], platform: "all", output_type: "persona", example_output: "# Persona: Marketing Maya\n\n**Age:** 28-35\n**Role:** Marketing Manager\n**Goals:** Automate content creation...", agent: "strategist" },
    ],
  },
  {
    id: "content-strategy",
    name: "Content Strategy Planner",
    description: "Develop a comprehensive content calendar with topic clusters, SEO targets, and distribution channels.",
    icon: "📅",
    category: "strategy",
    platforms: ["blog", "social", "email"],
    tools_used: ["Azure OpenAI", "SEMrush", "Brand Memory"],
    workflow_stages: ["Audit Current Content", "Identify Gaps", "Plan Topics", "Build Calendar", "Review"],
    default_llm: "gpt-4o",
    fallback_llms: ["gpt-4o-mini"],
    prompts: [
      { id: "plan", name: "Plan Strategy", description: "Generate a content strategy document", variables: ["business_goals", "target_audience", "existing_channels", "timeframe"], platform: "all", output_type: "strategy", example_output: "# Q3 Content Strategy\n\n## Pillar Topics\n1. AI in Marketing\n2. Data-Driven Campaigns...", agent: "strategist" },
      { id: "calendar", name: "Build Calendar", description: "Create a monthly content calendar", variables: ["month", "channels", "topics", "frequency"], platform: "all", output_type: "calendar", example_output: "| Week | Blog | LinkedIn | Email | Twitter |\n|------|------|----------|-------|---------|\n| 1 | AI Trends 2026 | Thought leadership | Newsletter | Thread |", agent: "strategist" },
    ],
  },
  {
    id: "seo-brief",
    name: "SEO Content Brief",
    description: "Generate keyword-optimized content briefs with search intent analysis, competitor gaps, and outline structure.",
    icon: "🔍",
    category: "strategy",
    platforms: ["blog", "web"],
    tools_used: ["Azure OpenAI", "SEMrush"],
    workflow_stages: ["Keyword Research", "Competitor Analysis", "Intent Mapping", "Generate Brief", "Review"],
    default_llm: "gpt-4o",
    fallback_llms: ["gpt-4o-mini"],
    prompts: [
      { id: "brief", name: "Generate Brief", description: "Create an SEO-optimized content brief", variables: ["primary_keyword", "secondary_keywords", "target_audience", "word_count"], platform: "blog", output_type: "brief", example_output: "# SEO Brief: AI Marketing Automation\n\n**Primary KW:** ai marketing automation (2,400 mo)\n**Intent:** Informational → Commercial\n**H2 Outline:**\n1. What is AI Marketing?...", agent: "seo_specialist" },
    ],
  },
  {
    id: "blog-writer",
    name: "Blog Post Writer",
    description: "Write long-form blog posts with SEO optimization, structured headings, and engaging narrative flow.",
    icon: "✍️",
    category: "execution",
    platforms: ["blog"],
    tools_used: ["Azure OpenAI", "Brand Memory", "SEMrush"],
    workflow_stages: ["Research", "Outline", "Draft", "SEO Review", "Final Edit", "Approval"],
    default_llm: "gpt-4o",
    fallback_llms: ["gpt-4o-mini", "gemini-1.5-pro"],
    prompts: [
      { id: "draft", name: "Write Draft", description: "Generate a full blog post", variables: ["topic", "target_keyword", "target_audience", "tone", "word_count"], platform: "blog", output_type: "article", example_output: "# How AI Is Transforming Marketing in 2026\n\nMarketing teams are increasingly turning to AI-powered tools...", agent: "copywriter" },
      { id: "outline", name: "Create Outline", description: "Build a structured outline", variables: ["topic", "key_points", "target_audience"], platform: "blog", output_type: "outline", example_output: "## Outline: AI Marketing Guide\n\n1. Introduction (hook + thesis)\n2. The Current State of AI in Marketing\n   - Key statistics...", agent: "copywriter" },
    ],
  },
  {
    id: "social-copy",
    name: "Social Media Copy",
    description: "Create platform-specific social media posts with hashtags, CTAs, and engagement hooks.",
    icon: "📱",
    category: "execution",
    platforms: ["linkedin", "twitter", "instagram"],
    tools_used: ["Azure OpenAI", "Brand Memory", "Buffer"],
    workflow_stages: ["Brief", "Draft Variants", "Review", "Schedule"],
    default_llm: "gpt-4o",
    fallback_llms: ["gpt-4o-mini"],
    prompts: [
      { id: "post", name: "Write Post", description: "Generate a social media post", variables: ["topic", "platform", "tone", "cta"], platform: "social", output_type: "post", example_output: "🚀 We just launched our AI marketing platform and the results are incredible.\n\nIn the first 30 days:\n→ 3x content output\n→ 40% less time on drafts\n→ 95% brand voice consistency\n\n#AIMarketing #MarTech", agent: "copywriter" },
      { id: "thread", name: "Create Thread", description: "Build a multi-post thread", variables: ["topic", "key_points", "platform"], platform: "social", output_type: "thread", example_output: "1/ AI is quietly revolutionizing how marketing teams work. Here's what we've learned:\n\n2/ First: The content bottleneck is real...", agent: "copywriter" },
    ],
  },
  {
    id: "email-campaign",
    name: "Email Campaign Writer",
    description: "Craft email sequences with subject lines, preview text, body copy, and A/B test variants.",
    icon: "📧",
    category: "execution",
    platforms: ["email"],
    tools_used: ["Azure OpenAI", "Brand Memory", "Mailchimp", "SendGrid"],
    workflow_stages: ["Strategy", "Draft Sequence", "A/B Variants", "Review", "Send"],
    default_llm: "gpt-4o",
    fallback_llms: ["gpt-4o-mini"],
    prompts: [
      { id: "sequence", name: "Write Sequence", description: "Generate a multi-email campaign", variables: ["campaign_goal", "audience_segment", "email_count", "tone"], platform: "email", output_type: "sequence", example_output: "## Email 1: Welcome\n**Subject:** Welcome to the future of marketing\n**Preview:** See what AI can do for your team\n\nHi {{first_name}},...", agent: "copywriter" },
      { id: "single", name: "Write Single", description: "Write one email with A/B variants", variables: ["purpose", "audience", "key_message", "cta"], platform: "email", output_type: "email", example_output: "**Variant A:**\nSubject: Your marketing just got smarter\n\n**Variant B:**\nSubject: 3x your content output with AI", agent: "copywriter" },
    ],
  },
  {
    id: "ad-copy",
    name: "Ad Copy Generator",
    description: "Generate high-converting ad copy for Google, Meta, and LinkedIn with headline variants.",
    icon: "📢",
    category: "execution",
    platforms: ["google-ads", "meta", "linkedin"],
    tools_used: ["Azure OpenAI", "Brand Memory"],
    workflow_stages: ["Brief", "Generate Variants", "Review", "Export"],
    default_llm: "gpt-4o",
    fallback_llms: ["gpt-4o-mini"],
    prompts: [
      { id: "generate", name: "Generate Ads", description: "Create ad copy with multiple variants", variables: ["product", "target_audience", "platform", "budget_range", "cta"], platform: "ads", output_type: "ad_copy", example_output: "## Google Search Ad\n**Headline 1:** AI Marketing Platform | 3x Output\n**Headline 2:** Automate Content Creation\n**Description:** Join 500+ teams using AI agents...", agent: "copywriter" },
    ],
  },
  {
    id: "social-scheduler",
    name: "Social Scheduler",
    description: "Schedule and publish content across social platforms with optimal timing suggestions.",
    icon: "⏰",
    category: "distribution",
    platforms: ["buffer", "linkedin"],
    tools_used: ["Buffer", "LinkedIn API", "Azure OpenAI"],
    workflow_stages: ["Select Content", "Optimize Timing", "Schedule", "Confirm"],
    default_llm: "gpt-4o-mini",
    fallback_llms: ["gpt-4o"],
    prompts: [
      { id: "schedule", name: "Schedule Posts", description: "Queue posts with optimal timing", variables: ["content", "platforms", "timezone", "frequency"], platform: "social", output_type: "schedule", example_output: "Scheduled 5 posts:\n- Mon 9:00 AM EST → LinkedIn\n- Tue 12:00 PM EST → Twitter\n- Wed 2:00 PM EST → LinkedIn...", agent: "social_publisher" },
    ],
  },
  {
    id: "campaign-analytics",
    name: "Campaign Analytics",
    description: "Analyze campaign performance across channels with actionable insights and optimization recommendations.",
    icon: "📊",
    category: "distribution",
    platforms: ["all"],
    tools_used: ["Azure OpenAI", "Google Analytics", "LinkedIn Analytics"],
    workflow_stages: ["Collect Data", "Analyze Metrics", "Generate Insights", "Recommend Actions"],
    default_llm: "gpt-4o",
    fallback_llms: ["gpt-4o-mini"],
    prompts: [
      { id: "report", name: "Generate Report", description: "Create a performance analytics report", variables: ["campaign_name", "date_range", "channels", "kpis"], platform: "all", output_type: "report", example_output: "# Campaign Performance: Q2 Product Launch\n\n## Summary\n- Total reach: 125K\n- Engagement rate: 4.2% (+1.1% vs Q1)\n- Conversions: 340\n- CPL: $12.50...", agent: "analyst" },
    ],
  },
  {
    id: "competitive-intel",
    name: "Competitive Intelligence",
    description: "Monitor competitor content, messaging, and positioning to identify opportunities and gaps.",
    icon: "🕵️",
    category: "strategy",
    platforms: ["all"],
    tools_used: ["Azure OpenAI", "SEMrush", "Web Scraping"],
    workflow_stages: ["Identify Competitors", "Collect Content", "Analyze Positioning", "Report"],
    default_llm: "gpt-4o",
    fallback_llms: ["gpt-4o-mini"],
    prompts: [
      { id: "analyze", name: "Analyze Competitor", description: "Deep-dive on a competitor's strategy", variables: ["competitor_name", "competitor_url", "your_positioning", "focus_areas"], platform: "all", output_type: "analysis", example_output: "# Competitive Analysis: Acme Corp\n\n## Content Strategy\n- Blog frequency: 3x/week\n- Key topics: AI automation, enterprise productivity\n- Tone: Corporate, data-heavy...", agent: "strategist" },
    ],
  },
  {
    id: "product-launch",
    name: "Product Launch Kit",
    description: "Generate a complete product launch package: press release, landing page copy, email blasts, and social campaigns.",
    icon: "🚀",
    category: "execution",
    platforms: ["all"],
    tools_used: ["Azure OpenAI", "Brand Memory", "DALL·E", "Canva"],
    workflow_stages: ["Brief", "Press Release", "Landing Page", "Email Sequence", "Social Campaign", "Review All"],
    default_llm: "gpt-4o",
    fallback_llms: ["gpt-4o-mini", "gemini-1.5-pro"],
    prompts: [
      { id: "kit", name: "Generate Launch Kit", description: "Create full product launch materials", variables: ["product_name", "product_description", "launch_date", "target_audience", "key_features", "pricing"], platform: "all", output_type: "launch_kit", example_output: "# Launch Kit: Zeta IMA v1.0\n\n## Press Release\nFOR IMMEDIATE RELEASE\n\nZeta Unveils AI Marketing Agency Platform...\n\n## Landing Page Copy\n**Hero:** Your AI Marketing Team, Ready to Work...", agent: "coordinator" },
    ],
  },
];

/** Look up a skill by ID from the static catalog */
export function getStaticSkill(id: string): StaticSkill | undefined {
  return STATIC_SKILLS.find((s) => s.id === id);
}
