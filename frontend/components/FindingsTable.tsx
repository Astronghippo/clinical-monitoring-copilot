"use client";
import React from "react";
import { clsx } from "clsx";
import type { Finding } from "@/lib/types";

const SEV_STYLES: Record<string, string> = {
  critical: "bg-red-100 text-red-800",
  major: "bg-amber-100 text-amber-800",
  minor: "bg-slate-100 text-slate-700",
};

const ANALYZER_LABEL: Record<string, string> = {
  visit_windows: "Visit window",
  completeness: "Completeness",
  eligibility: "Eligibility",
};

interface Props {
  findings: Finding[];
  onSelect?: (f: Finding) => void;
}

export function FindingsTable({ findings, onSelect }: Props) {
  if (findings.length === 0) {
    return <p className="text-slate-500">No findings yet.</p>;
  }
  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-left text-slate-600">
          <tr>
            <th className="px-3 py-2">Severity</th>
            <th className="px-3 py-2">Analyzer</th>
            <th className="px-3 py-2">Subject</th>
            <th className="px-3 py-2">Finding</th>
            <th className="px-3 py-2">Confidence</th>
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
              <td className="px-3 py-2 font-mono">{f.subject_id}</td>
              <td className="px-3 py-2">{f.summary}</td>
              <td className="px-3 py-2 text-slate-500">
                {(f.confidence * 100).toFixed(0)}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
