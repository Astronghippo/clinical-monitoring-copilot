"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { AnalysisSummary } from "@/lib/types";
import { Breadcrumbs } from "@/components/Breadcrumbs";

function formatTimestamp(iso: string): string {
  // Server returns naive UTC — append Z so JS parses correctly.
  const hasTZ = /Z$|[+-]\d{2}:?\d{2}$/.test(iso);
  const d = new Date(hasTZ ? iso : iso + "Z");
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

const STATUS_STYLES: Record<string, string> = {
  done: "bg-emerald-100 text-emerald-800",
  error: "bg-red-100 text-red-800",
  running: "bg-blue-100 text-blue-800",
  pending: "bg-slate-100 text-slate-700",
};

export default function AnalysisListPage() {
  const [analyses, setAnalyses] = useState<AnalysisSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listAnalyses()
      .then(setAnalyses)
      .catch((e) => setError((e as Error).message));
  }, []);

  return (
    <main className="space-y-6">
      <Breadcrumbs items={[{ label: "Home", href: "/" }, { label: "Analyses" }]} />

      <Link
        href="/"
        className="inline-flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900"
      >
        ← Upload new protocol &amp; dataset
      </Link>

      <header>
        <h1 className="text-2xl font-bold">Past analyses</h1>
        <p className="text-slate-600">
          Every analysis you&apos;ve run is saved. Click a row to reopen findings
          without re-running the analyzers.
        </p>
      </header>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          Failed to load list: {error}
        </div>
      )}

      {analyses === null && !error && (
        <p className="text-slate-500">Loading…</p>
      )}

      {analyses !== null && analyses.length === 0 && (
        <div className="rounded-lg border border-slate-200 bg-white p-8 text-center text-slate-500 shadow-sm">
          <p>No analyses yet.</p>
          <Link
            href="/"
            className="mt-3 inline-block rounded bg-slate-900 px-3 py-1.5 text-sm font-medium text-white"
          >
            Start your first analysis
          </Link>
        </div>
      )}

      {analyses !== null && analyses.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-slate-600">
              <tr>
                <th className="px-3 py-2">Name</th>
                <th className="px-3 py-2">Started</th>
                <th className="px-3 py-2">Protocol</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2 text-right">Findings</th>
              </tr>
            </thead>
            <tbody>
              {analyses.map((a) => (
                <tr
                  key={a.id}
                  className="border-t border-slate-100 hover:bg-slate-50"
                >
                  <td className="px-3 py-2">
                    <Link
                      href={`/analyses/${a.id}`}
                      className="text-slate-700 hover:text-slate-900 hover:underline"
                    >
                      {a.name ? (
                        <>
                          <span className="font-medium">{a.name}</span>
                          <span className="ml-2 font-mono text-xs text-slate-400">
                            #{a.id}
                          </span>
                        </>
                      ) : (
                        <span className="font-mono">Analysis #{a.id}</span>
                      )}
                    </Link>
                  </td>
                  <td className="px-3 py-2 text-slate-600">
                    {formatTimestamp(a.created_at)}
                  </td>
                  <td className="px-3 py-2">
                    {a.study_id ? (
                      <span className="font-mono">{a.study_id}</span>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    <span
                      className={`rounded px-2 py-0.5 text-xs font-medium ${
                        STATUS_STYLES[a.status] ?? "bg-slate-100 text-slate-700"
                      }`}
                    >
                      {a.status}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right">
                    {a.finding_count > 0 ? (
                      <span className="inline-flex items-center gap-1 text-slate-600">
                        {a.counts.critical > 0 && (
                          <span className="rounded bg-red-100 px-1.5 py-0.5 text-xs text-red-800">
                            {a.counts.critical} critical
                          </span>
                        )}
                        {a.counts.major > 0 && (
                          <span className="rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-800">
                            {a.counts.major} major
                          </span>
                        )}
                        {a.counts.minor > 0 && (
                          <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-700">
                            {a.counts.minor} minor
                          </span>
                        )}
                      </span>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
