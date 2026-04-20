"use client";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Analysis, AnalyzerKind, Finding, FindingGroup, Severity, FindingStatus, SiteRollup, SubjectDrilldown } from "@/lib/types";
import { FindingsTable } from "@/components/FindingsTable";
import { GroupedFindingsTable } from "@/components/GroupedFindingsTable";
import { SiteHeatmap } from "@/components/SiteHeatmap";
import { FindingDetail } from "@/components/FindingDetail";
import { FindingsFilterBar } from "@/components/FindingsFilterBar";
import { ProgressIndicator } from "@/components/ProgressIndicator";
import { EditableHeading } from "@/components/EditableHeading";
import { BulkActionsBar } from "@/components/BulkActionsBar";
import { SubjectPanel } from "@/components/SubjectPanel";
import { AmendmentDiff } from "@/components/AmendmentDiff";
import { DigestPanel } from "@/components/DigestPanel";
import { NLFilterBar } from "@/components/NLFilterBar";
import type { NLFilters } from "@/components/NLFilterBar";

const SEVERITY_ORDER: Record<Severity, number> = { critical: 0, major: 1, minor: 2 };

function downloadCsv(findings: Finding[], analysisId: number) {
  const escape = (v: unknown) => {
    const s = v === null || v === undefined ? "" : String(v);
    // RFC 4180: wrap in quotes, escape embedded quotes by doubling them.
    return `"${s.replace(/"/g, '""')}"`;
  };
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
  const lines = [headers.join(",")];
  for (const f of findings) {
    lines.push(
      [
        escape(f.id),
        escape(f.analyzer),
        escape(f.severity),
        escape(f.subject_id),
        escape(f.summary),
        escape(f.detail),
        escape(f.protocol_citation),
        escape(f.confidence),
      ].join(","),
    );
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
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  // Filter state — persisted as URL query params would be nicer, but
  // component-local state is fine for now.
  const [severityFilter, setSeverityFilter] = useState<Severity[]>([
    "critical",
    "major",
    "minor",
  ]);
  const [analyzerFilter, setAnalyzerFilter] = useState<AnalyzerKind | "all">("all");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<FindingStatus[]>(["open", "in_review"]);
  const [activeTab, setActiveTab] = useState<"findings" | "grouped" | "sites">("findings");
  const [groups, setGroups] = useState<FindingGroup[] | null>(null);
  const [siteRollup, setSiteRollup] = useState<SiteRollup[] | null>(null);
  const [selectedSubject, setSelectedSubject] = useState<string | null>(null);
  const [subjectData, setSubjectData] = useState<SubjectDrilldown | null>(null);
  const [showAmendmentDiff, setShowAmendmentDiff] = useState(false);
  const [showDigest, setShowDigest] = useState(false);

  useEffect(() => {
    if (activeTab === "grouped" && analysis && groups === null) {
      api.listGroupedFindings(analysis.id).then(setGroups);
    }
    if (activeTab === "sites" && analysis && siteRollup === null) {
      api.getSiteRollup(analysis.id).then(setSiteRollup);
    }
  }, [activeTab, analysis, groups, siteRollup]);

  useEffect(() => {
    if (!selectedSubject || !analysis) return;
    let cancelled = false;
    setSubjectData(null);
    api.getSubjectDrilldown(analysis.id, selectedSubject)
      .then((data) => { if (!cancelled) setSubjectData(data); })
      .catch(() => { if (!cancelled) setSelectedSubject(null); });
    return () => { cancelled = true; };
  }, [selectedSubject, analysis]);

  // Close subject panel on ESC for a11y (mirrors FindingDetail ESC handler).
  useEffect(() => {
    if (!selectedSubject) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setSelectedSubject(null);
        setSubjectData(null);
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [selectedSubject]);

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

  useEffect(() => {
    if (!showAmendmentDiff) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setShowAmendmentDiff(false);
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [showAmendmentDiff]);

  const filtered = useMemo(() => {
    if (!analysis) return [];
    const q = search.trim().toLowerCase();
    const rows = analysis.findings.filter((f) => {
      if (!severityFilter.includes(f.severity)) return false;
      if (analyzerFilter !== "all" && f.analyzer !== analyzerFilter) return false;
      if (!statusFilter.includes(f.status)) return false;
      if (
        q &&
        !f.subject_id.toLowerCase().includes(q) &&
        !f.summary.toLowerCase().includes(q)
      )
        return false;
      return true;
    });
    const sorted = [...rows].sort(
      (a, b) =>
        SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity] ||
        a.subject_id.localeCompare(b.subject_id),
    );
    return sorted;
  }, [analysis, severityFilter, analyzerFilter, search, statusFilter]);

  const findingsById = useMemo(() => {
    const m = new Map<number, Finding>();
    if (analysis) for (const f of analysis.findings) m.set(f.id, f);
    return m;
  }, [analysis]);

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

  function toggleStatus(s: FindingStatus) {
    setStatusFilter((prev) =>
      prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s],
    );
  }

  function toggleSelected(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function clearSelection() {
    setSelectedIds(new Set());
  }

  async function bulkStatus(status: FindingStatus) {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) return;
    await api.bulkUpdateStatus(ids, status);
    setAnalysis((prev) =>
      prev
        ? {
            ...prev,
            findings: prev.findings.map((f) =>
              selectedIds.has(f.id) ? { ...f, status } : f,
            ),
          }
        : prev,
    );
    clearSelection();
  }

  async function bulkDraftLetters() {
    if (!analysis) return;
    const ids = Array.from(selectedIds);
    const letters = await Promise.all(ids.map((id) => api.draftQueryLetter(id)));
    const body = letters
      .map((l) => `Subject: ${l.subject_line}\n\n${l.body}\n\nReply by: ${l.reply_by}`)
      .join("\n\n=====\n\n");
    const blob = new Blob([body], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `query-letters-analysis-${analysis.id}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    clearSelection();
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
          <EditableHeading
            value={analysis.name}
            fallback={`Analysis #${analysis.id}`}
            onSave={async (next) => {
              const updated = await api.renameAnalysis(analysis.id, next);
              // Keep findings that we already polled — only refresh metadata.
              setAnalysis((prev) =>
                prev ? { ...prev, name: updated.name } : updated,
              );
            }}
          />
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
            <>
              <div className="flex gap-2 mb-4">
                <a
                  href={`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/analyses/${analysis.id}/report.pdf`}
                  className="inline-flex items-center gap-1 rounded border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700 hover:bg-slate-50"
                >
                  Download PDF report
                </a>
                <button
                  onClick={() => setShowAmendmentDiff(true)}
                  className="inline-flex items-center gap-1 rounded border border-blue-200 bg-blue-50 px-2 py-1 text-xs text-blue-700 hover:bg-blue-100"
                >
                  Check Amendment
                </button>
                <button
                  onClick={() => setShowDigest((v) => !v)}
                  className="inline-flex items-center gap-1 rounded border border-violet-200 bg-violet-50 px-2 py-1 text-xs text-violet-700 hover:bg-violet-100"
                >
                  {showDigest ? "Hide digest" : "Weekly digest"}
                </button>
              </div>
              {showDigest && (
                <div className="mb-4">
                  <DigestPanel analysisId={analysis.id} />
                </div>
              )}
              <div className="mb-3">
                <NLFilterBar
                  analysisId={analysis.id}
                  onFiltersApplied={(f: NLFilters) => {
                    if (f.analyzer) setAnalyzerFilter(f.analyzer as typeof analyzerFilter);
                    else setAnalyzerFilter("all");
                    if (f.severity) setSeverityFilter(f.severity as Severity[]);
                    else setSeverityFilter(["critical", "major", "minor"]);
                    if (f.search_text) setSearch(f.search_text);
                    else setSearch("");
                  }}
                />
              </div>
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
                statusFilter={statusFilter}
                onToggleStatus={toggleStatus}
              />
            </>
          )}

          <BulkActionsBar
            count={selectedIds.size}
            onClear={clearSelection}
            onBulkStatus={bulkStatus}
            onBulkDraftLetters={bulkDraftLetters}
          />

          {/* Tab bar */}
          <div className="flex gap-1 border-b border-slate-200 mb-4">
            {(["findings", "grouped", "sites"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 text-sm font-medium rounded-t border-b-2 transition-colors ${
                  activeTab === tab
                    ? "border-blue-600 text-blue-700 bg-blue-50"
                    : "border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                }`}
              >
                {tab === "grouped" ? "Grouped" : tab === "sites" ? "Sites" : "Findings"}
              </button>
            ))}
          </div>

          {activeTab === "grouped" && groups ? (
            <GroupedFindingsTable
              groups={groups.filter(
                (g) =>
                  severityFilter.includes(g.severity) &&
                  (analyzerFilter === "all" || g.analyzer === analyzerFilter),
              )}
              findingsById={findingsById}
              onSelect={setSelected}
            />
          ) : activeTab === "sites" && siteRollup !== null ? (
            <SiteHeatmap sites={siteRollup} />
          ) : activeTab === "sites" ? (
            <p className="text-slate-500">Loading site data…</p>
          ) : (
            <FindingsTable
              findings={filtered}
              onSelect={setSelected}
              onStatusChange={async (id, next) => {
                await api.updateFinding(id, { status: next });
                setAnalysis((prev) =>
                  prev
                    ? {
                        ...prev,
                        findings: prev.findings.map((f) =>
                          f.id === id ? { ...f, status: next } : f,
                        ),
                      }
                    : prev,
                );
              }}
              selectedIds={selectedIds}
              onToggleSelected={toggleSelected}
              onSubjectClick={(subjectId) => setSelectedSubject(subjectId)}
            />
          )}
        </>
      )}

      {/* Subject drill-down panel */}
      {selectedSubject && (
        <SubjectPanel
          subjectId={selectedSubject}
          data={subjectData}
          onClose={() => {
            setSelectedSubject(null);
            setSubjectData(null);
          }}
        />
      )}

      {/* Modal: Amendment diff panel */}
      {showAmendmentDiff && (
        <div
          role="presentation"
          onClick={() => setShowAmendmentDiff(false)}
          className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/40 p-4 md:items-center"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label="Amendment diff"
            className="w-full max-w-xl"
          >
            <AmendmentDiff
              analysisId={analysis.id}
              findings={analysis.findings}
              onClose={() => setShowAmendmentDiff(false)}
            />
          </div>
        </div>
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
