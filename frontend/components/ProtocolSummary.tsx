"use client";
import type { ProtocolSpec } from "@/lib/types";

interface Props {
  spec: ProtocolSpec;
}

function formatWindow(minus: number, plus: number): string {
  if (minus === 0 && plus === 0) return "no window";
  if (minus === plus) return `±${plus} day${plus === 1 ? "" : "s"}`;
  return `-${minus} / +${plus} days`;
}

export function ProtocolSummary({ spec }: Props) {
  const inclusions = spec.eligibility.filter((c) => c.kind === "inclusion");
  const exclusions = spec.eligibility.filter((c) => c.kind === "exclusion");

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm">
      <p className="mb-3 text-slate-600">
        Claude extracted the following structure from your protocol. Verify it
        looks right before running analysis.
      </p>

      {spec.visits.length > 0 && (
        <div className="mb-4">
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Schedule of assessments ({spec.visits.length} visits)
          </h4>
          <div className="overflow-hidden rounded border border-slate-200 bg-white">
            <table className="w-full text-xs">
              <thead className="bg-slate-50 text-left text-slate-600">
                <tr>
                  <th className="px-2 py-1.5">ID</th>
                  <th className="px-2 py-1.5">Visit</th>
                  <th className="px-2 py-1.5">Nominal day</th>
                  <th className="px-2 py-1.5">Window</th>
                  <th className="px-2 py-1.5">Required procedures</th>
                </tr>
              </thead>
              <tbody>
                {spec.visits.map((v) => (
                  <tr key={v.visit_id} className="border-t border-slate-100">
                    <td className="px-2 py-1.5 font-mono">{v.visit_id}</td>
                    <td className="px-2 py-1.5">{v.name}</td>
                    <td className="px-2 py-1.5 font-mono">Day {v.nominal_day}</td>
                    <td className="px-2 py-1.5">
                      {formatWindow(v.window_minus_days, v.window_plus_days)}
                    </td>
                    <td className="px-2 py-1.5 text-slate-600">
                      {v.required_procedures.length > 0
                        ? v.required_procedures.join(", ")
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {spec.eligibility.length > 0 && (
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Eligibility ({inclusions.length} inclusion, {exclusions.length} exclusion)
          </h4>
          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded border border-slate-200 bg-white p-2">
              <p className="mb-1 text-xs font-semibold text-emerald-700">Inclusion</p>
              <ul className="space-y-1 text-xs text-slate-700">
                {inclusions.map((c) => (
                  <li key={c.criterion_id}>
                    <span className="font-mono text-slate-500">{c.criterion_id}</span>{" "}
                    {c.text}
                  </li>
                ))}
              </ul>
            </div>
            <div className="rounded border border-slate-200 bg-white p-2">
              <p className="mb-1 text-xs font-semibold text-red-700">Exclusion</p>
              <ul className="space-y-1 text-xs text-slate-700">
                {exclusions.map((c) => (
                  <li key={c.criterion_id}>
                    <span className="font-mono text-slate-500">{c.criterion_id}</span>{" "}
                    {c.text}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
