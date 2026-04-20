"use client";
import React, { useState } from "react";
import { clsx } from "clsx";
import type { Finding, FindingStatus } from "@/lib/types";
import { FindingStatusBadge } from "./FindingStatusBadge";

const SEV_STYLES: Record<string, string> = {
  critical: "bg-red-100 text-red-800",
  major: "bg-amber-100 text-amber-800",
  minor: "bg-slate-100 text-slate-700",
};

const ANALYZER_LABEL: Record<string, string> = {
  visit_windows: "Visit window",
  completeness: "Completeness",
  eligibility: "Eligibility",
  plausibility: "Plausibility",
};

interface Props {
  findings: Finding[];
  onSelect?: (f: Finding) => void;
  onStatusChange?: (id: number, next: FindingStatus) => Promise<void>;
  selectedIds?: Set<number>;
  onToggleSelected?: (id: number) => void;
  onSubjectClick?: (subjectId: string) => void;
  analysisId?: number;
}

export function FindingsTable({
  findings,
  onSelect,
  onStatusChange,
  selectedIds,
  onToggleSelected,
  onSubjectClick,
  analysisId,
}: Props) {
  const [copiedId, setCopiedId] = useState<number | null>(null);

  function handleCopyLink(e: React.MouseEvent, findingId: number) {
    e.stopPropagation();
    const url = `${window.location.origin}/analyses/${analysisId}?finding=${findingId}`;
    navigator.clipboard.writeText(url).then(() => {
      setCopiedId(findingId);
      setTimeout(() => setCopiedId(null), 1500);
    });
  }
  if (findings.length === 0) {
    return <p className="text-slate-500">No findings match the current filters.</p>;
  }
  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-left text-slate-600">
          <tr>
            {onToggleSelected && <th className="px-3 py-2 w-10">✓</th>}
            <th className="px-3 py-2">Severity</th>
            <th className="px-3 py-2">Analyzer</th>
            <th className="px-3 py-2">Subject</th>
            <th className="px-3 py-2">Finding</th>
            <th className="px-3 py-2">Confidence</th>
            {onStatusChange && <th className="px-3 py-2">Status</th>}
            {analysisId !== undefined && <th className="px-3 py-2 w-10"></th>}
          </tr>
        </thead>
        <tbody>
          {findings.map((f) => (
            <tr
              key={f.id}
              className="cursor-pointer border-t border-slate-100 hover:bg-slate-50"
              onClick={() => onSelect?.(f)}
              data-testid={`finding-row-${f.id}`}
            >
              {onToggleSelected && (
                <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                  <input
                    type="checkbox"
                    checked={selectedIds?.has(f.id) ?? false}
                    onChange={() => onToggleSelected(f.id)}
                    className="rounded border-slate-300"
                  />
                </td>
              )}
              <td className="px-3 py-2">
                <span
                  className={clsx(
                    "rounded px-2 py-0.5 text-xs font-medium",
                    SEV_STYLES[f.severity],
                  )}
                >
                  {f.severity}
                </span>
              </td>
              <td className="px-3 py-2 text-slate-600">
                {ANALYZER_LABEL[f.analyzer] ?? f.analyzer}
              </td>
              <td className="px-3 py-2 font-mono">
                {onSubjectClick ? (
                  <button
                    type="button"
                    className="text-blue-600 hover:underline font-mono"
                    onClick={(e) => {
                      e.stopPropagation();
                      onSubjectClick(f.subject_id);
                    }}
                  >
                    {f.subject_id}
                  </button>
                ) : (
                  f.subject_id
                )}
              </td>
              <td className="px-3 py-2">{f.summary}</td>
              <td className="px-3 py-2 text-slate-500">
                {(f.confidence * 100).toFixed(0)}%
              </td>
              {onStatusChange && (
                <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                  <FindingStatusBadge
                    value={f.status}
                    onChange={(next) => onStatusChange(f.id, next)}
                  />
                </td>
              )}
              {analysisId !== undefined && (
                <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                  <button
                    type="button"
                    aria-label="Copy link to finding"
                    className="text-slate-400 hover:text-slate-700 text-xs px-1"
                    onClick={(e) => handleCopyLink(e, f.id)}
                  >
                    {copiedId === f.id ? "✓" : "🔗"}
                  </button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
