"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft, Play, ChevronDown, ChevronUp, Loader2,
  CheckCircle, ExternalLink,
} from "lucide-react";
import clsx from "clsx";
import { skills } from "@/lib/api";

type Prompt = {
  id: string;
  name: string;
  description: string;
  variables: string[];
  platform: string;
  output_type: string;
  example_output: string;
  agent: string;
};

type SkillDetail = {
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
  prompts: Prompt[];
};

export default function SkillDetailPage() {
  const params = useParams();
  const router = useRouter();
  const skillId = params.id as string;

  const [skill, setSkill] = useState<SkillDetail | null>(null);
  const [selectedPrompt, setSelectedPrompt] = useState<Prompt | null>(null);
  const [variables, setVariables] = useState<Record<string, string>>({});
  const [expandedPrompt, setExpandedPrompt] = useState<string | null>(null);
  const [executing, setExecuting] = useState(false);
  const [result, setResult] = useState<{ workflow_id: string; message: string } | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    skills.get(skillId).then((data) => {
      setSkill(data);
      if (data.prompts.length > 0) {
        setSelectedPrompt(data.prompts[0]);
        // Initialize variables
        const vars: Record<string, string> = {};
        data.prompts[0].variables.forEach((v: string) => (vars[v] = ""));
        setVariables(vars);
      }
    });
  }, [skillId]);

  const selectPrompt = (prompt: Prompt) => {
    setSelectedPrompt(prompt);
    setResult(null);
    setError("");
    const vars: Record<string, string> = {};
    prompt.variables.forEach((v) => (vars[v] = ""));
    setVariables(vars);
  };

  const execute = async () => {
    if (!selectedPrompt || !skill) return;

    const missing = selectedPrompt.variables.filter((v) => !variables[v]?.trim());
    if (missing.length > 0) {
      setError(`Please fill in: ${missing.join(", ")}`);
      return;
    }

    setExecuting(true);
    setError("");
    setResult(null);

    try {
      const res = await skills.execute(skillId, {
        prompt_id: selectedPrompt.id,
        variables,
      });
      setResult(res);
    } catch (e: any) {
      setError(e.message || "Execution failed");
    } finally {
      setExecuting(false);
    }
  };

  if (!skill) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="animate-spin text-gray-400" size={24} />
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      {/* Back + Header */}
      <Link href="/skills" className="flex items-center gap-1 text-sm text-gray-500 hover:text-brand mb-6">
        <ArrowLeft size={14} /> Back to Skills
      </Link>

      <div className="flex items-start justify-between mb-6">
        <div>
          <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">{skill.category}</span>
          <h1 className="text-2xl font-bold text-gray-900 mt-1">{skill.name}</h1>
          <p className="text-gray-500 mt-1 max-w-2xl">{skill.description}</p>
        </div>
        <div className="flex gap-1 flex-wrap">
          {skill.platforms.map((p) => (
            <span key={p} className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-lg">{p}</span>
          ))}
        </div>
      </div>

      {/* Workflow Stages */}
      {skill.workflow_stages.length > 0 && (
        <div className="bg-gray-50 rounded-xl p-4 mb-6">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Workflow Stages</h3>
          <div className="flex items-center gap-2 flex-wrap">
            {skill.workflow_stages.map((stage, i) => (
              <div key={i} className="flex items-center gap-2">
                <span className="bg-white border rounded-lg px-3 py-1.5 text-xs text-gray-700">{stage}</span>
                {i < skill.workflow_stages.length - 1 && (
                  <span className="text-gray-300">&rarr;</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Prompt List (left) */}
        <div className="lg:col-span-2 space-y-2">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">
            Prompts ({skill.prompts.length})
          </h2>
          {skill.prompts.map((prompt) => (
            <div key={prompt.id}>
              <button
                onClick={() => selectPrompt(prompt)}
                className={clsx(
                  "w-full text-left p-3 rounded-xl border transition-all",
                  selectedPrompt?.id === prompt.id
                    ? "border-brand bg-blue-50 shadow-sm"
                    : "border-gray-200 bg-white hover:border-gray-300"
                )}
              >
                <div className="flex items-center justify-between">
                  <h4 className="font-medium text-sm text-gray-900">{prompt.name}</h4>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setExpandedPrompt(expandedPrompt === prompt.id ? null : prompt.id);
                    }}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    {expandedPrompt === prompt.id ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>
                </div>
                <p className="text-xs text-gray-500 mt-0.5">{prompt.description}</p>
                <div className="flex gap-2 mt-2">
                  <span className="text-[10px] bg-gray-100 px-1.5 py-0.5 rounded text-gray-500">
                    {prompt.agent} agent
                  </span>
                  <span className="text-[10px] bg-gray-100 px-1.5 py-0.5 rounded text-gray-500">
                    {prompt.output_type}
                  </span>
                  <span className="text-[10px] bg-gray-100 px-1.5 py-0.5 rounded text-gray-500">
                    {prompt.variables.length} var{prompt.variables.length !== 1 ? "s" : ""}
                  </span>
                </div>
              </button>

              {/* Expanded: show example output */}
              {expandedPrompt === prompt.id && prompt.example_output && (
                <div className="mt-1 ml-2 p-3 bg-gray-50 border border-gray-100 rounded-lg">
                  <h5 className="text-[10px] font-semibold text-gray-400 uppercase mb-1">Example Output</h5>
                  <pre className="text-xs text-gray-600 whitespace-pre-wrap font-mono">
                    {prompt.example_output.slice(0, 500)}
                    {prompt.example_output.length > 500 ? "..." : ""}
                  </pre>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Execute Panel (right) */}
        <div className="lg:col-span-3">
          {selectedPrompt ? (
            <div className="bg-white border rounded-xl p-5 sticky top-8">
              <h3 className="font-semibold text-gray-900 mb-1">{selectedPrompt.name}</h3>
              <p className="text-xs text-gray-500 mb-4">{selectedPrompt.description}</p>

              {/* Variable inputs */}
              <div className="space-y-3 mb-5">
                {selectedPrompt.variables.map((v) => (
                  <div key={v}>
                    <label className="block text-xs font-medium text-gray-600 mb-1">
                      {v.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}
                    </label>
                    <textarea
                      rows={v.includes("description") || v.includes("context") || v.includes("content") ? 4 : 2}
                      value={variables[v] || ""}
                      onChange={(e) => setVariables({ ...variables, [v]: e.target.value })}
                      className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand resize-none"
                      placeholder={`Enter ${v.replace(/_/g, " ")}...`}
                    />
                  </div>
                ))}
              </div>

              {/* LLM info */}
              <div className="flex items-center gap-2 mb-4 text-xs text-gray-400">
                <span>Default LLM: <strong className="text-gray-600">{skill.default_llm}</strong></span>
                <span>|</span>
                <span>Fallbacks: {skill.fallback_llms.join(", ")}</span>
              </div>

              {/* Error */}
              {error && (
                <div className="bg-red-50 text-red-700 text-xs px-3 py-2 rounded-lg mb-3">
                  {error}
                </div>
              )}

              {/* Success */}
              {result && (
                <div className="bg-green-50 border border-green-200 text-green-700 text-sm px-4 py-3 rounded-xl mb-3">
                  <div className="flex items-center gap-2">
                    <CheckCircle size={14} />
                    <span>{result.message}</span>
                  </div>
                  <Link
                    href={`/workflows?highlight=${result.workflow_id}`}
                    className="flex items-center gap-1 text-xs mt-2 text-green-600 hover:underline"
                  >
                    View Workflow <ExternalLink size={12} />
                  </Link>
                </div>
              )}

              {/* Execute button */}
              <button
                onClick={execute}
                disabled={executing}
                className="w-full flex items-center justify-center gap-2 bg-brand hover:bg-blue-700 text-white py-2.5 rounded-xl text-sm font-medium disabled:opacity-50 transition-colors"
              >
                {executing ? (
                  <>
                    <Loader2 size={14} className="animate-spin" /> Executing...
                  </>
                ) : (
                  <>
                    <Play size={14} /> Start Workflow
                  </>
                )}
              </button>
            </div>
          ) : (
            <div className="text-center py-20 text-gray-400">
              Select a prompt to get started
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
