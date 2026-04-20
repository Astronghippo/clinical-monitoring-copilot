"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AnalysisSummary } from "@/lib/types";

const STATUS_CLASSES: Record<AnalysisSummary["status"], string> = {
  done: "bg-green-100 text-green-800",
  running: "bg-blue-100 text-blue-800",
  pending: "bg-slate-100 text-slate-600",
  error: "bg-red-100 text-red-700",
};

function CountChip({
  count,
  label,
  className,
}: {
  count: number;
  label: string;
  className: string;
}) {
  if (count === 0) return null;
  return (
    <span
      title={`${count} ${label}`}
      className={`inline-flex items-center rounded px-1.5 py-0.5 text-xs font-semibold ${className}`}
    >
      {count}
      <span className="ml-0.5 font-normal">{label[0]}</span>
    </span>
  );
}

export function RecentAnalyses() {
  const [analyses, setAnalyses] = useState<AnalysisSummary[] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .listAnalyses()
      .then((list) => {
        const sorted = [...list].sort(
          (a, b) =>
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
        );
        setAnalyses(sorted.slice(0, 3));
      })
      .catch(() => {
        setAnalyses([]);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <p className="text-sm text-slate-500">Loading recent analyses…</p>;
  }

  if (!analyses || analyses.length === 0) {
    return null;
  }

  return (
    <section className="space-y-2">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-800">Recent analyses</h2>
        <a
          href="/analyses"
          className="text-sm text-violet-600 hover:underline"
        >
          View all →
        </a>
      </div>

      <ul className="space-y-2">
        {analyses.map((a) => {
          const displayName = a.name ?? `Analysis #${a.id}`;
          return (
            <li
              key={a.id}
              className="flex items-center justify-between rounded-lg border border-slate-200 bg-white px-4 py-2.5 shadow-sm"
            >
              <div className="flex flex-col gap-0.5">
                <a
                  href={`/analyses/${a.id}`}
                  className="text-sm font-medium text-slate-900 hover:underline"
                >
                  {displayName}
                </a>
                {a.study_id && (
                  <span className="text-xs text-slate-500">{a.study_id}</span>
                )}
              </div>

              <div className="flex items-center gap-2">
                <CountChip
                  count={a.counts.critical}
                  label="critical"
                  className="bg-red-100 text-red-800"
                />
                <CountChip
                  count={a.counts.major}
                  label="major"
                  className="bg-amber-100 text-amber-800"
                />
                <CountChip
                  count={a.counts.minor}
                  label="minor"
                  className="bg-yellow-100 text-yellow-800"
                />
                <span
                  className={`rounded px-2 py-0.5 text-xs font-medium capitalize ${STATUS_CLASSES[a.status]}`}
                >
                  {a.status}
                </span>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
