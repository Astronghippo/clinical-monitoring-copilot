"use client";
import { useState } from "react";
import type { SiteRollup } from "@/lib/types";

type SortKey = "site_id" | "subject_count" | "finding_count" | "deviation_rate";
type SortDir = "asc" | "desc";

interface Props {
  sites: SiteRollup[];
}

export function SiteHeatmap({ sites }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("site_id");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  if (sites.length === 0) {
    return <p className="text-slate-500">No site data available.</p>;
  }

  function handleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  const sorted = [...sites].sort((a, b) => {
    let cmp = 0;
    if (sortKey === "site_id") {
      cmp = a.site_id.localeCompare(b.site_id);
    } else {
      cmp = a[sortKey] - b[sortKey];
    }
    return sortDir === "asc" ? cmp : -cmp;
  });

  function SortIndicator({ col }: { col: SortKey }) {
    if (sortKey !== col) return <span className="text-slate-300 ml-1">↕</span>;
    return <span className="ml-1">{sortDir === "asc" ? "↑" : "↓"}</span>;
  }

  function th(label: string, key: SortKey) {
    return (
      <th
        className="px-3 py-2 text-left cursor-pointer select-none hover:bg-slate-100"
        onClick={() => handleSort(key)}
      >
        {label}
        <SortIndicator col={key} />
      </th>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-slate-600">
          <tr>
            {th("Site ID", "site_id")}
            {th("Subjects", "subject_count")}
            {th("Total Findings", "finding_count")}
            {th("Deviation Rate", "deviation_rate")}
            <th className="px-3 py-2 text-left text-red-700">Critical</th>
            <th className="px-3 py-2 text-left text-amber-700">Major</th>
            <th className="px-3 py-2 text-left text-slate-600">Minor</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((site) => (
            <tr
              key={site.site_id}
              data-testid={`site-row-${site.site_id}`}
              className="border-t border-slate-100 hover:bg-slate-50"
            >
              <td className="px-3 py-2 font-medium text-slate-800">{site.site_id}</td>
              <td
                className="px-3 py-2 text-slate-700"
                data-testid={`subject-count-${site.site_id}`}
              >
                {site.subject_count}
              </td>
              <td
                className="px-3 py-2 text-slate-700"
                data-testid={`finding-count-${site.site_id}`}
              >
                {site.finding_count}
              </td>
              <td
                className="px-3 py-2 text-slate-700"
                data-testid={`deviation-rate-${site.site_id}`}
              >
                {site.deviation_rate.toFixed(1)} per subject
              </td>
              <td
                className="px-3 py-2 text-red-700 font-medium"
                data-testid={`critical-count-${site.site_id}`}
              >
                {site.counts.critical}
              </td>
              <td
                className="px-3 py-2 text-amber-700 font-medium"
                data-testid={`major-count-${site.site_id}`}
              >
                {site.counts.major}
              </td>
              <td
                className="px-3 py-2 text-slate-600"
                data-testid={`minor-count-${site.site_id}`}
              >
                {site.counts.minor}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
