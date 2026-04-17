"use client";
import React from "react";
import type { Finding } from "@/lib/types";
import { X } from "lucide-react";

interface Props {
  finding: Finding;
  onClose: () => void;
}

export function FindingDetail({ finding, onClose }: Props) {
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
    </aside>
  );
}
