"use client";
import { Download } from "lucide-react";
import type { AnalyzerKind, Severity, FindingStatus } from "@/lib/types";

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
  grouped: boolean;
  onToggleGrouped: () => void;
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
  grouped,
  onToggleGrouped,
}: Props) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
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
            className="rounded border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700"
          >
            <option value="all">All</option>
            <option value="visit_windows">Visit window</option>
            <option value="completeness">Completeness</option>
            <option value="eligibility">Eligibility</option>
          </select>
        </div>

        {/* Search */}
        <div className="flex flex-1 items-center gap-2">
          <input
            type="search"
            value={search}
            onChange={(e) => onChangeSearch(e.target.value)}
            placeholder="Search subject ID or finding text…"
            className="w-full min-w-[200px] rounded border border-slate-200 bg-white px-2 py-1 text-sm text-slate-700 placeholder-slate-400"
          />
        </div>

        {/* Group toggle */}
        <label className="inline-flex items-center gap-1 text-xs text-slate-600">
          <input type="checkbox" checked={grouped} onChange={onToggleGrouped} />
          Group similar
        </label>

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
        </div>
      </div>
    </div>
  );
}
