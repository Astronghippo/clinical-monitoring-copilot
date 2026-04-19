"use client";
import React from "react";
import { clsx } from "clsx";
import type { SubjectDrilldown } from "@/lib/types";

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

const STATUS_STYLES: Record<string, string> = {
  open: "bg-blue-100 text-blue-800",
  in_review: "bg-amber-100 text-amber-800",
  resolved: "bg-green-100 text-green-800",
  false_positive: "bg-slate-100 text-slate-600",
};

interface Props {
  subjectId: string;
  data: SubjectDrilldown | null;
  onClose: () => void;
}

export function SubjectPanel({ subjectId, data, onClose }: Props) {
  return (
    <>
      {/* Backdrop */}
      <div
        role="presentation"
        className="fixed inset-0 z-40 bg-slate-900/30"
        onClick={onClose}
      />
      {/* Slide-in panel */}
      <aside
        role="dialog"
        aria-modal="true"
        aria-label={`Subject ${subjectId}`}
        className="fixed right-0 top-0 z-50 flex h-full w-96 flex-col bg-white shadow-xl"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <h2 className="text-base font-semibold">Subject {subjectId}</h2>
          <button
            type="button"
            aria-label="Close"
            onClick={onClose}
            className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {data === null ? (
          <div className="flex flex-1 items-center justify-center text-slate-500">
            Loading…
          </div>
        ) : (
          <div className="flex flex-1 flex-col overflow-hidden">
            {/* Visit timeline */}
            <div className="border-b border-slate-200 px-4 py-3">
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Visit Timeline
              </h3>
              <div className="flex flex-wrap gap-2">
                {data.visits.map((v) => (
                  <span
                    key={v.visit_name}
                    data-testid={`visit-chip-${v.visit_name}`}
                    className={clsx(
                      "rounded-full px-3 py-1 text-xs font-medium",
                      v.has_finding
                        ? "bg-red-100 text-red-800"
                        : "bg-green-100 text-green-800",
                    )}
                    title={v.date ?? undefined}
                  >
                    {v.visit_name}
                  </span>
                ))}
                {data.visits.length === 0 && (
                  <p className="text-xs text-slate-400">No visits recorded.</p>
                )}
              </div>
            </div>

            {/* Findings list */}
            <div className="flex-1 overflow-y-auto px-4 py-3">
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Findings ({data.findings.length})
              </h3>
              <div className="space-y-2">
                {data.findings.map((f) => (
                  <div
                    key={f.id}
                    className="rounded-lg border border-slate-200 bg-slate-50 p-3"
                  >
                    <div className="mb-1 flex items-center gap-2">
                      <span
                        className={clsx(
                          "rounded px-2 py-0.5 text-xs font-medium",
                          SEV_STYLES[f.severity],
                        )}
                      >
                        {f.severity}
                      </span>
                      <span
                        className={clsx(
                          "rounded px-2 py-0.5 text-xs font-medium",
                          STATUS_STYLES[f.status] ?? "bg-slate-100 text-slate-600",
                        )}
                      >
                        {f.status.replace("_", " ")}
                      </span>
                      <span className="ml-auto text-xs text-slate-500">
                        {ANALYZER_LABEL[f.analyzer] ?? f.analyzer}
                      </span>
                    </div>
                    <p className="text-sm text-slate-800">{f.summary}</p>
                  </div>
                ))}
                {data.findings.length === 0 && (
                  <p className="text-sm text-slate-500">No findings for this subject.</p>
                )}
              </div>
            </div>
          </div>
        )}
      </aside>
    </>
  );
}
