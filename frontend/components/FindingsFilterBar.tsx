"use client";
import React from "react";
import { Download } from "lucide-react";
import type { AnalyzerKind, Severity, FindingStatus } from "@/lib/types";
import { Tooltip } from "./Tooltip";

interface Props {
  severityFilter: Severity[];
  onToggleSeverity: (sev: Severity) => void;
  analyzerFilter: AnalyzerKind | "all";
  onChangeAnalyzer: (a: AnalyzerKind | "all") => void;
  search: string;
  onChangeSearch: (s: string) => void;
  filteredCount: number;
  totalCount: number;
  onExportCsv: () => void;
  statusFilter: FindingStatus[];
  onToggleStatus: (s: FindingStatus) => void;
  minConfidence: number;
  onChangeMinConfidence: (v: number) => void;
  searchInputRef?: React.RefObject<HTMLInputElement>;
}

const SEVERITY_BUTTON: Record<Severity, string> = {
  critical: "bg-red-100 text-red-800 border-red-200",
  major: "bg-amber-100 text-amber-800 border-amber-200",
  minor: "bg-slate-100 text-slate-700 border-slate-200",
};

export function FindingsFilterBar({
  severityFilter,
  onToggleSeverity,
  analyzerFilter,
  onChangeAnalyzer,
  search,
  onChangeSearch,
  filteredCount,
  totalCount,
  onExportCsv,
  statusFilter,
  onToggleStatus,
  minConfidence,
  onChangeMinConfidence,
  searchInputRef,
}: Props) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm dark:border-gray-600 dark:bg-gray-800">
      <div className="flex flex-wrap items-center gap-3">
        {/* Severity toggle chips */}
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Severity:
          </span>
          {(["critical", "major", "minor"] as const).map((sev) => {
            const active = severityFilter.includes(sev);
            return (
              <button
                type="button"
                key={sev}
                onClick={() => onToggleSeverity(sev)}
                className={`rounded border px-2 py-0.5 text-xs font-medium transition ${
                  active
                    ? SEVERITY_BUTTON[sev]
                    : "border-slate-200 bg-white text-slate-400 hover:bg-slate-50"
                }`}
              >
                {sev}
              </button>
            );
          })}
        </div>

        {/* Status toggle chips */}
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Status:
          </span>
          {(["open", "in_review", "resolved", "false_positive"] as const).map((s) => {
            const active = statusFilter.includes(s);
            return (
              <button
                type="button"
                key={s}
                onClick={() => onToggleStatus(s)}
                className={`rounded border px-2 py-0.5 text-xs font-medium transition ${
                  active
                    ? "border-slate-300 bg-slate-100 text-slate-700"
                    : "border-slate-200 bg-white text-slate-400 hover:bg-slate-50"
                }`}
              >
                {s.replace("_", " ")}
              </button>
            );
          })}
        </div>

        {/* Analyzer filter */}
        <div className="flex items-center gap-2">
          <label
            htmlFor="analyzer-filter"
            className="text-xs font-semibold uppercase tracking-wide text-slate-500"
          >
            Analyzer:
          </label>
          <select
            id="analyzer-filter"
            value={analyzerFilter}
            onChange={(e) =>
              onChangeAnalyzer(e.target.value as AnalyzerKind | "all")
            }
            className="rounded border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
          >
            <option value="all">All</option>
            <option value="visit_windows">Visit window</option>
            <option value="completeness">Completeness</option>
            <option value="eligibility">Eligibility</option>
            <option value="plausibility">Plausibility</option>
          </select>
        </div>

        {/* Confidence slider */}
        <div className="flex items-center gap-2">
          <label
            htmlFor="confidence-slider"
            className="text-xs font-semibold uppercase tracking-wide text-slate-500"
          >
            Confidence:
          </label>
          <input
            id="confidence-slider"
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={minConfidence}
            onChange={(e) => onChangeMinConfidence(parseFloat(e.target.value))}
            className="w-24 accent-slate-600"
          />
          <span className="text-xs text-slate-600">
            {minConfidence < 0.005
              ? "All confidence"
              : `≥ ${Math.round(minConfidence * 100)}%`}
          </span>
        </div>

        {/* Search */}
        <div className="flex flex-1 items-center gap-2">
          <input
            ref={searchInputRef}
            type="search"
            value={search}
            onChange={(e) => onChangeSearch(e.target.value)}
            placeholder="Search subject ID or finding text…"
            className="w-full min-w-[200px] rounded border border-slate-200 bg-white px-2 py-1 text-sm text-slate-700 placeholder-slate-400 dark:border-gray-600 dark:bg-gray-800 dark:text-white dark:placeholder-gray-400"
          />
        </div>

        {/* Export + count */}
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-500">
            {filteredCount === totalCount
              ? `${totalCount} finding${totalCount === 1 ? "" : "s"}`
              : `${filteredCount} of ${totalCount} shown`}
          </span>
          <button
            type="button"
            onClick={onExportCsv}
            disabled={filteredCount === 0}
            className="inline-flex items-center gap-1 rounded border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            <Download size={14} />
            Download CSV
          </button>
          <Tooltip
            text="j/k: next/prev row · Enter: open · e: export · /: search"
            position="top"
          >
            <span
              className="inline-flex h-5 w-5 cursor-default items-center justify-center rounded-full border border-slate-300 bg-slate-50 text-xs font-bold text-slate-500 hover:bg-slate-100"
              aria-label="Keyboard shortcuts"
            >
              ?
            </span>
          </Tooltip>
        </div>
      </div>
    </div>
  );
}
