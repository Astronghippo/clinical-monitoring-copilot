"use client";
import { useState } from "react";
import { Check, Copy, Mail, X } from "lucide-react";
import { api } from "@/lib/api";
import type { Finding, QueryLetter } from "@/lib/types";

interface Props {
  finding: Finding;
  onClose: () => void;
}

export function FindingDetail({ finding, onClose }: Props) {
  const [letter, setLetter] = useState<QueryLetter | null>(null);
  const [drafting, setDrafting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function handleDraft() {
    setDrafting(true);
    setError(null);
    try {
      const l = await api.draftQueryLetter(finding.id);
      setLetter(l);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setDrafting(false);
    }
  }

  async function handleCopy() {
    if (!letter) return;
    const full = `Subject: ${letter.subject_line}\n\n${letter.body}`;
    try {
      await navigator.clipboard.writeText(full);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard may be blocked in some browsers; silently ignore.
    }
  }

  return (
    <aside
      role="dialog"
      aria-label="Finding detail"
      className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
    >
      <div className="mb-3 flex items-start justify-between">
        <div>
          <h3 className="text-lg font-semibold">{finding.summary}</h3>
          <p className="text-sm text-slate-500">
            Subject <span className="font-mono">{finding.subject_id}</span>
            {" · "}confidence {(finding.confidence * 100).toFixed(0)}%
          </p>
        </div>
        <button
          type="button"
          aria-label="Close"
          onClick={onClose}
          className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
        >
          <X size={18} />
        </button>
      </div>

      <section className="space-y-3">
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Explanation
          </h4>
          <p className="whitespace-pre-wrap text-sm text-slate-800">{finding.detail}</p>
        </div>
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Protocol citation
          </h4>
          <p className="font-mono text-sm text-slate-800">{finding.protocol_citation}</p>
        </div>
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Data citation
          </h4>
          <pre className="overflow-x-auto rounded bg-slate-50 p-2 text-xs text-slate-800">
{JSON.stringify(finding.data_citation, null, 2)}
          </pre>
        </div>
      </section>

      <section className="mt-5 border-t border-slate-100 pt-4">
        {!letter && (
          <button
            type="button"
            onClick={handleDraft}
            disabled={drafting}
            className="inline-flex items-center gap-2 rounded bg-slate-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            <Mail size={16} />
            {drafting ? "Drafting…" : "Draft query letter to site"}
          </button>
        )}
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}

        {letter && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Drafted query letter
              </h4>
              <button
                type="button"
                onClick={handleCopy}
                className="inline-flex items-center gap-1 rounded border border-slate-300 px-2 py-1 text-xs text-slate-700 hover:bg-slate-50"
              >
                {copied ? <Check size={14} /> : <Copy size={14} />}
                {copied ? "Copied" : "Copy"}
              </button>
            </div>
            <div className="rounded border border-slate-200 bg-slate-50 p-3">
              <p className="mb-2 text-sm">
                <span className="font-semibold">Subject:</span> {letter.subject_line}
              </p>
              <p className="whitespace-pre-wrap text-sm text-slate-800">{letter.body}</p>
              {letter.reply_by && (
                <p className="mt-3 text-xs text-slate-500">
                  Reply-by date: <span className="font-mono">{letter.reply_by}</span>
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={() => {
                setLetter(null);
                setError(null);
              }}
              className="text-xs text-slate-500 hover:text-slate-700"
            >
              Re-draft
            </button>
          </div>
        )}
      </section>
    </aside>
  );
}
