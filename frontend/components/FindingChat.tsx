"use client";
import { useState, useRef, useEffect } from "react";
import { SendHorizonal } from "lucide-react";
import { api } from "@/lib/api";
import type { ChatMessage, Finding } from "@/lib/types";

const STARTER_PROMPTS = [
  "Why was this flagged?",
  "What data supports this finding?",
  "What are the next steps?",
  "How severe is this issue?",
];

interface Props {
  finding: Finding;
}

export function FindingChat({ finding }: Props) {
  const [input, setInput] = useState("");
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView?.({ behavior: "smooth" });
  }, [history]);

  async function send(message: string) {
    if (!message.trim() || loading) return;
    setInput("");
    setError(null);
    setLoading(true);

    const nextHistory: ChatMessage[] = [
      ...history,
      { role: "user", content: message },
    ];
    setHistory(nextHistory);

    try {
      const { reply } = await api.chatFinding(finding.id, message, history);
      setHistory([...nextHistory, { role: "assistant", content: reply }]);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    send(input);
  }

  return (
    <div className="flex flex-col gap-3">
      {/* Starter chips — only shown before first message */}
      {history.length === 0 && (
        <div className="flex flex-wrap gap-2">
          {STARTER_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => setInput(prompt)}
              className="rounded-full border border-slate-300 bg-slate-50 px-3 py-1 text-xs text-slate-600 hover:bg-slate-100"
            >
              {prompt}
            </button>
          ))}
        </div>
      )}

      {/* Message thread */}
      {history.length > 0 && (
        <div className="max-h-64 space-y-3 overflow-y-auto rounded border border-slate-100 bg-slate-50 p-3 text-sm">
          {history.map((msg, i) => (
            <div
              key={i}
              className={
                msg.role === "user"
                  ? "text-right text-slate-700"
                  : "text-left text-slate-900"
              }
            >
              <span
                className={
                  msg.role === "user"
                    ? "inline-block rounded-lg bg-slate-200 px-3 py-2"
                    : "inline-block rounded-lg bg-white px-3 py-2 shadow-sm"
                }
              >
                {msg.content}
              </span>
            </div>
          ))}
          {loading && (
            <div className="text-left text-slate-400">
              <span className="inline-block animate-pulse rounded-lg bg-white px-3 py-2 shadow-sm">
                …
              </span>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      )}

      {error && <p className="text-xs text-red-600">{error}</p>}

      {/* Input */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about this finding…"
          disabled={loading}
          className="flex-1 rounded border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400 disabled:opacity-50"
        />
        <button
          type="submit"
          aria-label="Send"
          disabled={loading}
          className="inline-flex items-center gap-1 rounded bg-slate-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          <SendHorizonal size={14} />
          Send
        </button>
      </form>
    </div>
  );
}
