"use client";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Analysis, AnalyzerKind, Finding, Severity } from "@/lib/types";
import { FindingsTable } from "@/components/FindingsTable";
import { FindingDetail } from "@/components/FindingDetail";
import { FindingsFilterBar } from "@/components/FindingsFilterBar";
import { ProgressIndicator } from "@/components/ProgressIndicator";

function downloadCsv(findings: Finding[], analysisId: number) {
  const headers = [
    "id",
    "analyzer",
    "severity",
    "subject_id",
    "summary",
    "detail",
    "protocol_citation",
    "confidence",
  ];
  const escape = (v: unknown) => {
    const s = v === null || v === undefined ? "" : String(v);
    // RFC 4180: wrap in quotes, escape embedded quotes by doubling them.
    return `"${s.replace(/"/g, '""')}"`;
  };
  const lines = [headers.join(",")];
  for (const f of findings) {
    lines.push(headers.map((h) => escape((f as Record<string, unknown>)[h])).join(","));
  }
  const csv = lines.join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `analysis-${analysisId}-findings.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export default function AnalysisPage() {
  const params = useParams<{ id: string }>();
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [selected, setSelected] = useState<Finding | null>(null);

  // Filter state — persisted as URL query params would be nicer, but
  // component-local state is fine for now.
  const [severityFilter, setSeverityFilter] = useState<Severity[]>([
    "critical",
    "major",
    "minor",
  ]);
  const [analyzerFilter, setAnalyzerFilter] = useState<AnalyzerKind | "all">("all");
  const [search, setSearch] = useState("");

  useEffect(() => {
    let live = true;
    async function tick() {
      const a = await api.getAnalysis(Number(params.id));
      if (!live) return;
      setAnalysis(a);
      if (a.status === "pending" || a.status === "running") {
        setTimeout(tick, 1500);
      }
    }
    tick();
    return () => {
      live = false;
    };
  }, [params.id]);

  // Close modal on ESC for a11y.
  useEffect(() => {
    if (!selected) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSelected(null);
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [selected]);

  const filtered = useMemo(() => {
    if (!analysis) return [];
    const q = search.trim().toLowerCase();
    return analysis.findings.filter((f) => {
      if (!severityFilter.includes(f.severity)) return false;
      if (analyzerFilter !== "all" && f.analyzer !== analyzerFilter) return false;
      if (
        q &&
        !f.subject_id.toLowerCase().includes(q) &&
        !f.summary.toLowerCase().includes(q)
      )
        return false;
      return true;
    });
  }, [analysis, severityFilter, analyzerFilter, search]);

  if (!analysis) return <p className="text-slate-500">Loading…</p>;

  const counts = {
    critical: analysis.findings.filter((f) => f.severity === "critical").length,
    major: analysis.findings.filter((f) => f.severity === "major").length,
    minor: analysis.findings.filter((f) => f.severity === "minor").length,
  };

  const inProgress =
    analysis.status === "pending" || analysis.status === "running";
  const hasErrorFinding = analysis.findings.some(
    (f) => f.subject_id === "-" && f.severity === "critical",
  );

  function toggleSeverity(sev: Severity) {
    setSeverityFilter((prev) =>
      prev.includes(sev) ? prev.filter((s) => s !== sev) : [...prev, sev],
    );
  }

  return (
    <main className="space-y-6">
      <div className="flex items-center justify-between">
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900"
        >
          ← Run new analysis
        </Link>
        <Link
          href="/analyses"
          className="text-sm text-slate-600 hover:text-slate-900"
        >
          All past analyses →
        </Link>
      </div>

      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold">Analysis #{analysis.id}</h1>
          <p className="text-slate-600">
            Status: <b>{analysis.status}</b>
          </p>
        </div>
        {!inProgress && (
          <div className="flex gap-2 text-sm">
            <span className="rounded bg-red-100 px-2 py-1 text-red-800">
              Critical: {counts.critical}
            </span>
            <span className="rounded bg-amber-100 px-2 py-1 text-amber-800">
              Major: {counts.major}
            </span>
            <span className="rounded bg-slate-100 px-2 py-1 text-slate-700">
              Minor: {counts.minor}
            </span>
          </div>
        )}
      </header>

      {inProgress ? (
        <ProgressIndicator
          status={analysis.status}
          startedAt={analysis.created_at}
        />
      ) : (
        <>
          {analysis.status === "error" && !hasErrorFinding && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
              Analysis finished with errors — see the critical row below for details.
            </div>
          )}

          {analysis.findings.length > 0 && (
            <FindingsFilterBar
              severityFilter={severityFilter}
              onToggleSeverity={toggleSeverity}
              analyzerFilter={analyzerFilter}
              onChangeAnalyzer={setAnalyzerFilter}
              search={search}
              onChangeSearch={setSearch}
              filteredCount={filtered.length}
              totalCount={analysis.findings.length}
              onExportCsv={() => downloadCsv(filtered, analysis.id)}
            />
          )}

          <FindingsTable findings={filtered} onSelect={setSelected} />
        </>
      )}

      {/* Modal: FindingDetail over a backdrop, ESC or backdrop-click to dismiss. */}
      {selected && (
        <div
          role="presentation"
          onClick={() => setSelected(null)}
          className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/40 p-4 md:items-center"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            className="w-full max-w-2xl"
          >
            <FindingDetail finding={selected} onClose={() => setSelected(null)} />
          </div>
        </div>
      )}
    </main>
  );
}
