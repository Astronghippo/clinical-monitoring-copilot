"use client";
import { useState } from "react";
import { Check, Copy, RefreshCw, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { Tooltip } from "./Tooltip";

interface Props {
  analysisId: number;
}

export function DigestPanel({ analysisId }: Props) {
  const [digest, setDigest] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function generate() {
    setLoading(true);
    setError(null);
    try {
      const result = await api.generateDigest(analysisId);
      setDigest(result.digest);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function copy() {
    if (!digest) return;
    try {
      await navigator.clipboard.writeText(digest);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard blocked — silently ignore.
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        {!digest ? (
          <Tooltip text="Generate a weekly narrative summary of all findings using Claude AI">
            <button
              type="button"
              onClick={generate}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded border border-violet-200 bg-violet-50 px-3 py-1.5 text-sm font-medium text-violet-800 hover:bg-violet-100 disabled:opacity-50"
            >
              <Sparkles size={14} />
              {loading ? "Generating…" : "Generate digest"}
            </button>
          </Tooltip>
        ) : (
          <>
            <button
              type="button"
              onClick={generate}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50 disabled:opacity-50"
            >
              <RefreshCw size={12} />
              Regenerate
            </button>
            <button
              type="button"
              onClick={copy}
              className="inline-flex items-center gap-2 rounded border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50"
            >
              {copied ? <Check size={12} /> : <Copy size={12} />}
              {copied ? "Copied" : "Copy"}
            </button>
          </>
        )}
      </div>

      {error && <p className="text-xs text-red-600">{error}</p>}

      {digest && (
        <div className="rounded-lg border border-violet-100 bg-violet-50 p-4 text-sm leading-relaxed text-slate-800">
          {digest}
        </div>
      )}
    </div>
  );
}
