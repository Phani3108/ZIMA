"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import clsx from "clsx";
import { Paperclip, ChevronDown, ArrowRight } from "lucide-react";

export type ToolOption = {
  id: string;
  label: string;
  icon?: string;
};

type Props = {
  tools: ToolOption[];
  placeholder?: string;
  disabled?: boolean;
  onSubmit: (text: string, toolId: string | null, files?: File[]) => void;
};

export default function CommandBar({ tools, placeholder, disabled, onSubmit }: Props) {
  const [text, setText] = useState("");
  const [selectedTool, setSelectedTool] = useState<string | null>(null);
  const [toolOpen, setToolOpen] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const dropRef = useRef<HTMLDivElement>(null);

  const selectedLabel = selectedTool
    ? tools.find((t) => t.id === selectedTool)?.label || "Tool"
    : "Auto";

  // close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropRef.current && !dropRef.current.contains(e.target as Node)) setToolOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleSubmit = useCallback(() => {
    const val = text.trim();
    if (!val || disabled) return;
    onSubmit(val, selectedTool);
    setText("");
  }, [text, selectedTool, disabled, onSubmit]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // auto-resize textarea
  useEffect(() => {
    const el = inputRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = Math.min(el.scrollHeight, 120) + "px";
    }
  }, [text]);

  return (
    <div className="bg-white border-t border-gray-200 px-4 py-3 shadow-[0_-4px_16px_rgba(0,0,0,0.04)]">
      <div className="flex items-end gap-2 max-w-4xl mx-auto">
        {/* Attach */}
        <label
          className="shrink-0 p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 cursor-pointer transition-colors"
          title="Attach file"
        >
          <Paperclip className="w-4 h-4" />
          <input type="file" className="hidden" multiple />
        </label>

        {/* Tool selector */}
        <div ref={dropRef} className="relative shrink-0">
          <button
            onClick={() => setToolOpen(!toolOpen)}
            className={clsx(
              "flex items-center gap-1 text-xs font-medium px-3 py-2 rounded-lg border transition-colors",
              selectedTool
                ? "border-blue-200 bg-blue-50 text-blue-700"
                : "border-gray-200 bg-gray-50 text-gray-600 hover:bg-gray-100",
            )}
          >
            <span className="max-w-[80px] truncate">{selectedLabel}</span>
            <ChevronDown className="w-3 h-3" />
          </button>

          {toolOpen && (
            <div className="absolute bottom-full mb-1 left-0 w-48 bg-white border border-gray-200 rounded-xl shadow-lg py-1 z-20 animate-slide-in">
              <button
                onClick={() => { setSelectedTool(null); setToolOpen(false); }}
                className={clsx(
                  "w-full text-left px-3 py-2 text-xs hover:bg-gray-50",
                  !selectedTool ? "font-medium text-blue-600" : "text-gray-700",
                )}
              >
                🔮 Auto-detect
              </button>
              {tools.map((t) => (
                <button
                  key={t.id}
                  onClick={() => { setSelectedTool(t.id); setToolOpen(false); }}
                  className={clsx(
                    "w-full text-left px-3 py-2 text-xs hover:bg-gray-50",
                    selectedTool === t.id ? "font-medium text-blue-600" : "text-gray-700",
                  )}
                >
                  {t.icon || "🔧"} {t.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Input */}
        <textarea
          ref={inputRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          disabled={disabled}
          placeholder={placeholder || "Describe what you need..."}
          className="flex-1 resize-none rounded-xl border border-gray-200 bg-gray-50 px-4 py-2.5 text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400 disabled:opacity-50 transition"
        />

        {/* Send */}
        <button
          onClick={handleSubmit}
          disabled={!text.trim() || disabled}
          className={clsx(
            "shrink-0 p-2.5 rounded-xl transition-all",
            text.trim() && !disabled
              ? "bg-blue-600 text-white hover:bg-blue-700 shadow-sm"
              : "bg-gray-100 text-gray-300 cursor-not-allowed",
          )}
        >
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
