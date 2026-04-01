"use client";

import { useState } from "react";
import { Copy, Download, RefreshCw, Check, ExternalLink } from "lucide-react";

type PreviewPanelProps = {
  type: "text" | "image" | "html" | "design" | "social_mock" | "canva" | null;
  content: string;
  url?: string | null;
  metadata?: Record<string, any>;
  onEdit?: (instruction: string) => void;
  onRegenerate?: () => void;
};

export default function PreviewPanel({
  type,
  content,
  url,
  metadata,
  onEdit,
  onRegenerate,
}: PreviewPanelProps) {
  const [copied, setCopied] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [instruction, setInstruction] = useState("");

  const copyToClipboard = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleEdit = () => {
    if (instruction.trim() && onEdit) {
      onEdit(instruction);
      setInstruction("");
      setEditMode(false);
    }
  };

  return (
    <div className="bg-white border rounded-xl overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-3 py-2 bg-gray-50 border-b">
        <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
          {type === "image" ? "Generated Image" :
           type === "html" ? "Email Preview" :
           type === "design" || type === "canva" ? "Design Preview" :
           type === "social_mock" ? "Social Preview" :
           "Content Output"}
        </span>
        <div className="flex items-center gap-1">
          {content && (
            <button
              onClick={copyToClipboard}
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-brand px-2 py-1 rounded"
            >
              {copied ? <Check size={12} className="text-green-500" /> : <Copy size={12} />}
              {copied ? "Copied" : "Copy"}
            </button>
          )}
          {onRegenerate && (
            <button
              onClick={onRegenerate}
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-brand px-2 py-1 rounded"
            >
              <RefreshCw size={12} /> Regenerate
            </button>
          )}
          {url && (
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-brand px-2 py-1 rounded"
            >
              <ExternalLink size={12} /> Open
            </a>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {type === "image" && url && (
          <div className="space-y-3">
            <img
              src={url}
              alt="Generated image"
              className="w-full rounded-lg shadow-sm"
            />
            {metadata?.revised_prompt && (
              <p className="text-xs text-gray-400 italic">{metadata.revised_prompt}</p>
            )}
          </div>
        )}

        {type === "html" && content && (
          <iframe
            srcDoc={content}
            className="w-full h-[500px] border rounded-lg"
            sandbox="allow-same-origin"
            title="Email preview"
          />
        )}

        {(type === "design" || type === "canva") && url && (
          <iframe
            src={url}
            className="w-full h-[500px] border rounded-lg"
            allow="fullscreen"
            title="Design preview"
          />
        )}

        {type === "social_mock" && content && (
          <SocialMockup text={content} metadata={metadata} />
        )}

        {(type === "text" || !type) && content && (
          <div className="prose prose-sm max-w-none">
            <pre className="whitespace-pre-wrap font-sans text-sm text-gray-700 leading-relaxed">
              {content}
            </pre>
          </div>
        )}
      </div>

      {/* Edit via chat */}
      {onEdit && (
        <div className="px-4 pb-4">
          {editMode ? (
            <div className="flex gap-2">
              <input
                type="text"
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") handleEdit(); }}
                placeholder="Describe your change..."
                className="flex-1 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand"
                autoFocus
              />
              <button
                onClick={handleEdit}
                disabled={!instruction.trim()}
                className="bg-brand text-white px-3 py-2 rounded-lg text-sm disabled:opacity-50"
              >
                Apply
              </button>
              <button
                onClick={() => setEditMode(false)}
                className="border text-gray-500 px-3 py-2 rounded-lg text-sm"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={() => setEditMode(true)}
              className="text-xs text-brand hover:underline"
            >
              ✏️ Edit with instructions...
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function SocialMockup({
  text,
  metadata,
}: {
  text: string;
  metadata?: Record<string, any>;
}) {
  const platform = metadata?.platform || "linkedin";

  if (platform === "linkedin") {
    return (
      <div className="max-w-lg mx-auto bg-white border rounded-xl overflow-hidden shadow-sm">
        {/* LinkedIn header */}
        <div className="flex items-center gap-3 p-4 pb-2">
          <div className="w-10 h-10 rounded-full bg-brand flex items-center justify-center text-white font-bold text-sm">
            Z
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-900">Zeta Marketing</p>
            <p className="text-[11px] text-gray-500">AI Marketing Agency &bull; 1m</p>
          </div>
        </div>
        {/* Post content */}
        <div className="px-4 pb-3">
          <p className="text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">{text}</p>
        </div>
        {/* Image if present */}
        {metadata?.image_url && (
          <img src={metadata.image_url} alt="" className="w-full" />
        )}
        {/* Engagement bar */}
        <div className="px-4 py-2 border-t flex items-center justify-between text-xs text-gray-500">
          <span>👍 Like</span>
          <span>💬 Comment</span>
          <span>🔁 Repost</span>
          <span>📤 Send</span>
        </div>
      </div>
    );
  }

  // Twitter/X mockup
  return (
    <div className="max-w-lg mx-auto bg-white border rounded-xl overflow-hidden shadow-sm p-4">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-full bg-gray-900 flex items-center justify-center text-white font-bold text-sm shrink-0">
          Z
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-1">
            <span className="font-bold text-sm">Zeta Marketing</span>
            <span className="text-gray-500 text-sm">@zetaima &bull; now</span>
          </div>
          <p className="text-sm text-gray-800 mt-1 whitespace-pre-wrap">{text}</p>
          {metadata?.image_url && (
            <img src={metadata.image_url} alt="" className="w-full rounded-xl mt-3" />
          )}
          <div className="flex items-center justify-between mt-3 text-xs text-gray-500 max-w-[300px]">
            <span>💬 0</span>
            <span>🔁 0</span>
            <span>❤️ 0</span>
            <span>📊 0</span>
          </div>
        </div>
      </div>
    </div>
  );
}
