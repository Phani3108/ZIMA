"use client";

import { useState } from "react";
import clsx from "clsx";
import { CheckCircle2, Circle, ExternalLink, Settings2, Loader2, Plug } from "lucide-react";

type Props = {
  name: string;
  icon: string;
  connected: boolean;
  setupUrl?: string;
  docsUrl?: string;
  fieldLabel?: string;        // "API Key" | "MCP URL" etc.
  fieldType?: "apikey" | "mcp";
  onConnect?: (value: string) => Promise<boolean>;
  onOpenTool?: () => void;
};

export default function ToolCard({
  name, icon, connected: initialConnected, setupUrl, docsUrl,
  fieldLabel = "API Key", fieldType = "apikey",
  onConnect, onOpenTool,
}: Props) {
  const [connected, setConnected] = useState(initialConnected);
  const [configuring, setConfiguring] = useState(false);
  const [value, setValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleConnect = async () => {
    if (!value.trim()) return;
    setLoading(true);
    setError("");
    try {
      const ok = onConnect ? await onConnect(value) : true;
      if (ok) {
        setConnected(true);
        setConfiguring(false);
        setValue("");
      } else {
        setError("Connection failed. Check credentials.");
      }
    } catch {
      setError("Connection failed. Check credentials.");
    } finally {
      setLoading(false);
    }
  };

  /* ── Connected state ───────────────────────────────────────── */
  if (connected && !configuring) {
    return (
      <div className="min-w-[200px] max-w-[220px] shrink-0 border border-green-200 bg-white rounded-xl p-4 flex flex-col gap-3 transition-all">
        <div className="flex items-center gap-2.5">
          <span className="text-xl">{icon}</span>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-800 truncate">{name}</p>
            <div className="flex items-center gap-1 mt-0.5">
              <CheckCircle2 className="w-3 h-3 text-green-500" />
              <span className="text-[11px] text-green-600 font-medium">Connected</span>
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          {setupUrl && (
            <a
              href={setupUrl}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => { if (onOpenTool) { e.preventDefault(); onOpenTool(); } }}
              className="flex items-center gap-1 text-[11px] font-medium text-blue-600 hover:text-blue-700"
            >
              Open Tool <ExternalLink className="w-3 h-3" />
            </a>
          )}
          <button
            onClick={() => setConfiguring(true)}
            className="flex items-center gap-1 text-[11px] font-medium text-gray-500 hover:text-gray-700"
          >
            <Settings2 className="w-3 h-3" /> Configure
          </button>
        </div>
      </div>
    );
  }

  /* ── Not connected / configure state ───────────────────────── */
  return (
    <div className="min-w-[220px] max-w-[260px] shrink-0 border border-gray-200 bg-white rounded-xl p-4 flex flex-col gap-3 transition-all">
      <div className="flex items-center gap-2.5">
        <span className="text-xl">{icon}</span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-800 truncate">
            {name}
            {fieldType === "mcp" && (
              <span className="ml-1.5 text-[10px] font-medium text-purple-600 bg-purple-50 px-1.5 py-0.5 rounded">MCP</span>
            )}
          </p>
          <div className="flex items-center gap-1 mt-0.5">
            <Circle className="w-3 h-3 text-gray-300" />
            <span className="text-[11px] text-gray-400">Not connected</span>
          </div>
        </div>
      </div>

      <div>
        <label className="text-[11px] font-medium text-gray-500 mb-1 block">{fieldLabel}</label>
        <input
          type={fieldType === "apikey" ? "password" : "url"}
          placeholder={fieldType === "mcp" ? "https://mcp-server.example.com" : "sk-..."}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="w-full text-xs border border-gray-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400 bg-gray-50"
        />
      </div>

      {error && <p className="text-[11px] text-red-500">{error}</p>}

      <div className="flex items-center gap-2">
        <button
          onClick={handleConnect}
          disabled={loading || !value.trim()}
          className={clsx(
            "flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg transition-colors",
            value.trim()
              ? "bg-blue-600 text-white hover:bg-blue-700"
              : "bg-gray-100 text-gray-400 cursor-not-allowed",
          )}
        >
          {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Plug className="w-3 h-3" />}
          Connect
        </button>
        {docsUrl && (
          <a
            href={docsUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[11px] text-gray-500 hover:text-blue-600 flex items-center gap-1"
          >
            Docs <ExternalLink className="w-3 h-3" />
          </a>
        )}
        {configuring && (
          <button
            onClick={() => { setConfiguring(false); setError(""); }}
            className="text-[11px] text-gray-400 hover:text-gray-600 ml-auto"
          >
            Cancel
          </button>
        )}
      </div>
    </div>
  );
}
