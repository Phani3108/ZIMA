"use client";

import Link from "next/link";
import Image from "next/image";
import {
  MessageCircle, Sparkles, GitBranch, Brain, BarChart2,
  Upload, Settings, ArrowRight, CheckCircle, Zap, Users,
  Shield, Cpu, Target, Layers, Clock, ChevronRight,
} from "lucide-react";

/* ─── Data ──────────────────────────────────────────────────────── */

const FEATURES = [
  {
    icon: Cpu,
    title: "13 Specialized AI Agents",
    desc: "Strategy, copywriting, design, SEO, social, email, analytics — each managed by a purpose-built agent with its own role and expertise.",
    color: "text-blue-600 bg-blue-50",
  },
  {
    icon: GitBranch,
    title: "Multi-Stage Workflows",
    desc: "Chain agents into pipelines — from brief to published content — with human-in-the-loop approvals at every critical gate.",
    color: "text-purple-600 bg-purple-50",
  },
  {
    icon: Brain,
    title: "Learning Memory System",
    desc: "Every approval, rejection, and edit teaches the system. Brand voice, audience preferences, and quality standards improve over time.",
    color: "text-amber-600 bg-amber-50",
  },
  {
    icon: MessageCircle,
    title: "Natural Language Interface",
    desc: "Chat with your marketing team in plain English. Describe what you need — agents handle the rest via Microsoft Teams or the web UI.",
    color: "text-green-600 bg-green-50",
  },
  {
    icon: Shield,
    title: "Actor-Critic Reflection",
    desc: "Every piece of content is reviewed by a critic agent before it reaches you. Quality-gated outputs with confidence scores.",
    color: "text-red-600 bg-red-50",
  },
  {
    icon: Layers,
    title: "Codable Skills Engine",
    desc: "Pre-built marketing skills with customizable prompts. Blog posts, social campaigns, email sequences, ad copy — all parameterized.",
    color: "text-teal-600 bg-teal-50",
  },
];

const STEPS = [
  {
    num: "01",
    title: "Configure Your Stack",
    desc: "Connect your LLM provider (Azure OpenAI), set up infrastructure, and add integrations like Canva, LinkedIn, and Mailchimp.",
    href: "/settings",
    icon: Settings,
  },
  {
    num: "02",
    title: "Ingest Brand Knowledge",
    desc: "Upload brand guidelines, past campaigns, style guides, and product docs. Agents use this as grounding context for every output.",
    href: "/ingest",
    icon: Upload,
  },
  {
    num: "03",
    title: "Start a Conversation",
    desc: "Tell the system what you need — \"Write a product launch campaign for Q3\" — and watch agents collaborate to deliver it.",
    href: "/chat",
    icon: MessageCircle,
  },
  {
    num: "04",
    title: "Review & Approve",
    desc: "Agents present drafts for your review. Approve, request edits, or reject. Every decision trains the system to match your standards.",
    href: "/tasks",
    icon: CheckCircle,
  },
  {
    num: "05",
    title: "Track & Optimize",
    desc: "Monitor performance across campaigns, see what's working, and let the analytics agent surface actionable insights.",
    href: "/analytics",
    icon: BarChart2,
  },
];

const CAPABILITIES = [
  "Blog posts & long-form content",
  "Social media campaigns",
  "Email marketing sequences",
  "Ad copy (Google, Meta, LinkedIn)",
  "SEO content briefs & audits",
  "Product launch kits",
  "Competitive intelligence reports",
  "Brand voice guidelines",
  "Design briefs for Canva / Figma",
  "Campaign performance analytics",
  "Content calendar planning",
  "A/B test variant generation",
];

/* ─── Page ──────────────────────────────────────────────────────── */

export default function HomePage() {
  return (
    <div className="min-h-screen bg-white overflow-y-auto">
      {/* ─── Hero ─────────────────────────────────────────────── */}
      <section className="relative px-6 py-16 md:py-24 max-w-5xl mx-auto text-center">
        {/* Logo */}
        <div className="flex justify-center mb-8">
          <Image
            src="https://res.cloudinary.com/apideck/image/upload/v1618437828/icons/zeta-tech.jpg"
            alt="Zeta Logo"
            width={72}
            height={72}
            className="rounded-2xl shadow-lg"
            unoptimized
          />
        </div>

        <div className="inline-flex items-center gap-2 bg-blue-50 text-blue-700 text-xs font-semibold px-3 py-1.5 rounded-full mb-6">
          <Zap size={12} /> Intelligent Marketing Agency
        </div>

        <h1 className="text-4xl md:text-5xl font-bold text-gray-900 leading-tight mb-4">
          Your AI Marketing Team,<br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-purple-600">
            Ready to Work
          </span>
        </h1>

        <p className="text-lg text-gray-500 max-w-2xl mx-auto mb-8 leading-relaxed">
          Zeta IMA is an autonomous marketing agency powered by 13 specialized AI agents.
          From strategy to execution — content creation, design, SEO, email, social, and analytics —
          orchestrated through intelligent workflows with human-in-the-loop quality gates.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <Link
            href="/chat"
            className="flex items-center gap-2 bg-gray-900 hover:bg-gray-800 text-white px-6 py-3 rounded-xl text-sm font-semibold transition-colors shadow-lg shadow-gray-900/20"
          >
            <MessageCircle size={16} /> Start a Conversation
          </Link>
          <Link
            href="/skills"
            className="flex items-center gap-2 border border-gray-300 hover:border-gray-400 text-gray-700 px-6 py-3 rounded-xl text-sm font-semibold transition-colors"
          >
            <Sparkles size={16} /> Browse Skills Catalog
          </Link>
        </div>
      </section>

      {/* ─── Features ─────────────────────────────────────────── */}
      <section className="px-6 py-16 bg-gray-50 border-y border-gray-200">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-2xl font-bold text-gray-900">What Makes Zeta IMA Different</h2>
            <p className="text-sm text-gray-500 mt-2 max-w-lg mx-auto">
              Not just another AI writing tool. A full agency with roles, memory, coordination, and continuous learning.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {FEATURES.map((f) => (
              <div key={f.title} className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-shadow">
                <div className={`inline-flex items-center justify-center w-10 h-10 rounded-lg mb-4 ${f.color}`}>
                  <f.icon size={20} />
                </div>
                <h3 className="font-semibold text-gray-900 mb-1.5">{f.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Getting Started ──────────────────────────────────── */}
      <section className="px-6 py-16 max-w-5xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-2xl font-bold text-gray-900">Get Started in 5 Steps</h2>
          <p className="text-sm text-gray-500 mt-2">From zero to your first AI-generated campaign in minutes.</p>
        </div>

        <div className="space-y-4">
          {STEPS.map((step, i) => (
            <Link
              key={step.num}
              href={step.href}
              className="group flex items-start gap-5 bg-white border border-gray-200 rounded-xl p-5 hover:shadow-md hover:border-blue-200 transition-all"
            >
              <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-gray-900 text-white flex items-center justify-center font-bold text-sm">
                {step.num}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <step.icon size={16} className="text-blue-600" />
                  <h3 className="font-semibold text-gray-900">{step.title}</h3>
                </div>
                <p className="text-sm text-gray-500">{step.desc}</p>
              </div>
              <ChevronRight size={16} className="text-gray-300 group-hover:text-blue-500 mt-3 shrink-0 transition-colors" />
            </Link>
          ))}
        </div>
      </section>

      {/* ─── Capabilities ─────────────────────────────────────── */}
      <section className="px-6 py-16 bg-gray-50 border-y border-gray-200">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-10">
            <h2 className="text-2xl font-bold text-gray-900">What You Can Create</h2>
            <p className="text-sm text-gray-500 mt-2">Every capability backed by specialized agents, brand memory, and quality gates.</p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {CAPABILITIES.map((cap) => (
              <div key={cap} className="flex items-center gap-2.5 bg-white border border-gray-200 rounded-lg px-4 py-3">
                <CheckCircle size={14} className="text-green-500 shrink-0" />
                <span className="text-sm text-gray-700">{cap}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Architecture Overview ────────────────────────────── */}
      <section className="px-6 py-16 max-w-5xl mx-auto">
        <div className="text-center mb-10">
          <h2 className="text-2xl font-bold text-gray-900">How It Works</h2>
          <p className="text-sm text-gray-500 mt-2">The agent orchestration loop behind every request.</p>
        </div>

        <div className="flex flex-col md:flex-row gap-3 items-stretch justify-center">
          {[
            { icon: MessageCircle, label: "You Ask", sublabel: "Chat or skill prompt", color: "bg-blue-50 border-blue-200 text-blue-700" },
            { icon: Target, label: "Recall & Plan", sublabel: "Memory + meeting engine", color: "bg-purple-50 border-purple-200 text-purple-700" },
            { icon: Users, label: "Agents Execute", sublabel: "Pipeline of specialists", color: "bg-amber-50 border-amber-200 text-amber-700" },
            { icon: Shield, label: "Critic Reviews", sublabel: "Actor-critic loop", color: "bg-red-50 border-red-200 text-red-700" },
            { icon: CheckCircle, label: "You Approve", sublabel: "Human-in-the-loop gate", color: "bg-green-50 border-green-200 text-green-700" },
            { icon: Brain, label: "System Learns", sublabel: "Feedback → memory", color: "bg-teal-50 border-teal-200 text-teal-700" },
          ].map((step, i, arr) => (
            <div key={step.label} className="flex items-center gap-3">
              <div className={`flex flex-col items-center text-center border rounded-xl px-4 py-5 flex-1 min-w-[120px] ${step.color}`}>
                <step.icon size={24} className="mb-2" />
                <div className="text-sm font-semibold">{step.label}</div>
                <div className="text-[11px] opacity-75 mt-0.5">{step.sublabel}</div>
              </div>
              {i < arr.length - 1 && (
                <ArrowRight size={16} className="text-gray-300 shrink-0 hidden md:block" />
              )}
            </div>
          ))}
        </div>
      </section>

      {/* ─── Quick Links ──────────────────────────────────────── */}
      <section className="px-6 py-12 bg-gray-900 text-white">
        <div className="max-w-5xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { href: "/chat", label: "Chat", desc: "Talk to your agents", icon: MessageCircle },
              { href: "/skills", label: "Skills", desc: "Browse the catalog", icon: Sparkles },
              { href: "/dashboard", label: "Dashboard", desc: "Monitor workflows", icon: BarChart2 },
              { href: "/settings", label: "Settings", desc: "Configure services", icon: Settings },
            ].map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="group flex items-start gap-3 bg-gray-800 hover:bg-gray-700 rounded-xl p-4 transition-colors"
              >
                <link.icon size={18} className="text-gray-400 group-hover:text-white mt-0.5 shrink-0" />
                <div>
                  <div className="text-sm font-semibold">{link.label}</div>
                  <div className="text-xs text-gray-400 group-hover:text-gray-300">{link.desc}</div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Footer ───────────────────────────────────────────── */}
      <footer className="px-6 py-6 bg-gray-950 text-center">
        <div className="flex items-center justify-center gap-2 mb-2">
          <Image
            src="https://res.cloudinary.com/apideck/image/upload/v1618437828/icons/zeta-tech.jpg"
            alt="Zeta"
            width={20}
            height={20}
            className="rounded"
            unoptimized
          />
          <span className="text-sm text-gray-400 font-medium">Zeta IMA</span>
        </div>
        <p className="text-xs text-gray-500">
          Created &amp; Developed by Phani Marupaka for Zeta &copy; 2026 Better World Technology Pvt. Ltd.
        </p>
      </footer>
    </div>
  );
}
