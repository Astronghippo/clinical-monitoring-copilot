"use client";
import { useState, Fragment } from "react";
import { ChevronRight, ChevronDown } from "lucide-react";
import type { Finding, FindingGroup } from "@/lib/types";
import { FindingsTable } from "./FindingsTable";

const SEV_STYLES: Record<string, string> = {
  critical: "bg-red-100 text-red-800",
  major: "bg-amber-100 text-amber-800",
  minor: "bg-slate-100 text-slate-700",
};

interface Props {
  groups: FindingGroup[];
  findingsById: Map<number, Finding>;
  onSelect: (f: Finding) => void;
}

export function GroupedFindingsTable({ groups, findingsById, onSelect }: Props) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  if (groups.length === 0) {
    return <p className="text-slate-500">No findings.</p>;
  }

  function toggle(key: string) {
    setExpanded((p) => {
      const n = new Set(p);
      if (n.has(key)) n.delete(key);
      else n.add(key);
      return n;
    });
  }

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-left text-slate-600">
          <tr>
            <th className="px-3 py-2 w-8"></th>
            <th className="px-3 py-2">Severity</th>
            <th className="px-3 py-2">Template</th>
            <th className="px-3 py-2 text-right">Subjects</th>
          </tr>
        </thead>
        <tbody>
          {groups.map((g) => {
            const key = `${g.severity}|${g.analyzer}|${g.template}`;
            const isOpen = expanded.has(key);
            return (
              <Fragment key={key}>
                <tr
                  className="cursor-pointer border-t border-slate-100 hover:bg-slate-50"
                  onClick={() => toggle(key)}
                >
                  <td className="px-3 py-2 text-slate-400">
                    {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                  </td>
                  <td className="px-3 py-2">
                    <span className={`rounded px-2 py-0.5 text-xs font-medium ${SEV_STYLES[g.severity]}`}>
                      {g.severity}
                    </span>
                  </td>
                  <td className="px-3 py-2">{g.template}</td>
                  <td className="px-3 py-2 text-right font-medium">{g.count}</td>
                </tr>
                {isOpen && (
                  <tr>
                    <td colSpan={4} className="bg-slate-50 p-2">
                      <FindingsTable
                        findings={g.finding_ids
                          .map((id) => findingsById.get(id))
                          .filter(Boolean) as Finding[]}
                        onSelect={onSelect}
                      />
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
