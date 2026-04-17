"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import type { Analysis, Finding } from "@/lib/types";
import { FindingsTable } from "@/components/FindingsTable";
import { FindingDetail } from "@/components/FindingDetail";

export default function AnalysisPage() {
  const params = useParams<{ id: string }>();
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [selected, setSelected] = useState<Finding | null>(null);

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

  if (!analysis) return <p className="text-slate-500">Loading…</p>;

  const counts = {
    critical: analysis.findings.filter((f) => f.severity === "critical").length,
    major: analysis.findings.filter((f) => f.severity === "major").length,
    minor: analysis.findings.filter((f) => f.severity === "minor").length,
  };

  return (
    <main className="space-y-6">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold">Analysis #{analysis.id}</h1>
          <p className="text-slate-600">
            Status: <b>{analysis.status}</b>
          </p>
        </div>
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
      </header>

      <FindingsTable findings={analysis.findings} onSelect={setSelected} />

      {selected && (
        <FindingDetail finding={selected} onClose={() => setSelected(null)} />
      )}
    </main>
  );
}
