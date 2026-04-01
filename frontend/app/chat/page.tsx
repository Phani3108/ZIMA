"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Loader2, CheckCircle, XCircle } from "lucide-react";
import clsx from "clsx";

type Message =
  | { role: "user"; content: string }
  | { role: "assistant"; content: string; type?: string }
  | { role: "draft"; draft: string; review: Record<string, unknown>; iteration: number; brief: string };

const API_WS = process.env.NEXT_PUBLIC_API_URL?.replace("http", "ws") || "ws://localhost:8000";
const SESSION_ID = typeof crypto !== "undefined" ? crypto.randomUUID() : Math.random().toString(36).slice(2);

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [comment, setComment] = useState("");
  const wsRef = useRef<WebSocket | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const ws = new WebSocket(`${API_WS}/ws/chat/${SESSION_ID}`);
    wsRef.current = ws;

    ws.onmessage = (ev) => {
      const data = JSON.parse(ev.data);
      setLoading(false);

      if (data.type === "thinking") {
        setMessages((m) => [...m, { role: "assistant", content: data.text, type: "thinking" }]);
      } else if (data.type === "awaiting_approval") {
        setMessages((m) => [...m, { role: "draft", draft: data.draft, review: data.review, iteration: data.iteration, brief: data.brief }]);
      } else if (data.type === "done") {
        setMessages((m) => [
          ...m,
          { role: "assistant", content: "Approved and saved to brand memory.", type: "done" },
        ]);
      } else if (data.type === "tool_result" || data.type === "status") {
        setMessages((m) => [...m, { role: "assistant", content: data.text || JSON.stringify(data.tool_results || {}), type: data.type }]);
      } else if (data.type === "error") {
        setMessages((m) => [...m, { role: "assistant", content: `Error: ${data.text}`, type: "error" }]);
      }
    };

    return () => ws.close();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = useCallback(() => {
    if (!input.trim() || !wsRef.current) return;
    const brief = input.trim();
    setMessages((m) => [...m, { role: "user", content: brief }]);
    setInput("");
    setLoading(true);
    wsRef.current.send(JSON.stringify({ type: "message", brief, user_id: "web-user", session_id: SESSION_ID }));
  }, [input]);

  const decide = useCallback((decision: "approve" | "reject") => {
    if (!wsRef.current) return;
    setLoading(true);
    wsRef.current.send(JSON.stringify({ type: decision, comment }));
    setComment("");
    setMessages((m) => [...m, { role: "user", content: decision === "approve" ? "✓ Approved" : `✗ Rejected${comment ? `: ${comment}` : ""}` }]);
  }, [comment]);

  return (
    <div className="flex flex-col h-full max-w-3xl mx-auto px-4 py-6">
      <h1 className="text-xl font-semibold text-gray-800 mb-4">Zeta Chat</h1>

      {/* Message thread */}
      <div className="flex-1 space-y-4 overflow-y-auto pb-4">
        {messages.length === 0 && (
          <div className="text-gray-400 text-center mt-20">
            Send a brief and I'll draft copy for you.
            <br />
            <span className="text-sm">e.g. "Write a LinkedIn post about our Series A"</span>
          </div>
        )}

        {messages.map((msg, i) => {
          if (msg.role === "user") {
            return (
              <div key={i} className="flex justify-end">
                <div className="bg-brand text-white rounded-2xl rounded-tr-sm px-4 py-2 max-w-lg text-sm">{msg.content}</div>
              </div>
            );
          }

          if (msg.role === "draft") {
            const scores = (msg.review as any)?.scores || {};
            return (
              <div key={i} className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-gray-800">Draft #{msg.iteration}</span>
                  <span className="text-xs text-gray-400 truncate max-w-xs">{msg.brief}</span>
                </div>
                <p className="text-gray-700 text-sm whitespace-pre-wrap">{msg.draft}</p>

                {Object.keys(scores).length > 0 && (
                  <div className="flex gap-4 text-xs text-gray-500">
                    {Object.entries(scores).map(([k, v]) => (
                      <span key={k}>{k.replace("_", " ")}: <strong>{String(v)}/10</strong></span>
                    ))}
                  </div>
                )}

                <textarea
                  className="w-full text-sm border rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-brand resize-none"
                  rows={2}
                  placeholder="Optional feedback (shown to agent if you reject)..."
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                />

                <div className="flex gap-2">
                  <button
                    onClick={() => decide("approve")}
                    className="flex items-center gap-1 bg-green-600 hover:bg-green-700 text-white text-sm px-4 py-2 rounded-lg"
                  >
                    <CheckCircle size={14} /> Approve
                  </button>
                  <button
                    onClick={() => decide("reject")}
                    className="flex items-center gap-1 bg-red-600 hover:bg-red-700 text-white text-sm px-4 py-2 rounded-lg"
                  >
                    <XCircle size={14} /> Reject & Revise
                  </button>
                </div>
              </div>
            );
          }

          // Assistant message
          return (
            <div key={i} className="flex justify-start">
              <div className={clsx(
                "rounded-2xl rounded-tl-sm px-4 py-2 max-w-lg text-sm",
                (msg as any).type === "error" ? "bg-red-50 text-red-700" :
                (msg as any).type === "done" ? "bg-green-50 text-green-700" :
                (msg as any).type === "thinking" ? "bg-gray-100 text-gray-500 italic" :
                "bg-gray-100 text-gray-700"
              )}>
                {msg.content}
              </div>
            </div>
          );
        })}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-2xl rounded-tl-sm px-4 py-2">
              <Loader2 size={16} className="animate-spin text-gray-400" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="flex gap-2 pt-4 border-t">
        <textarea
          className="flex-1 border rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand resize-none"
          rows={2}
          placeholder="Enter brief... (Shift+Enter for new line, Enter to send)"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
        />
        <button
          onClick={send}
          disabled={loading || !input.trim()}
          className="bg-brand hover:bg-blue-700 text-white px-4 py-2 rounded-xl disabled:opacity-50"
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  );
}
