"use client";
import type { ProtocolOverview } from "@/lib/types";

interface Props {
  overview: ProtocolOverview;
}

/** Compact key/value pair used for the field grid. Hides itself when empty. */
function Field({ label, value }: { label: string; value: string | number | null }) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </p>
      <p className="text-sm text-slate-800">{value}</p>
    </div>
  );
}

export function ProtocolOverviewCard({ overview }: Props) {
  const hasArms = overview.arms && overview.arms.length > 0;
  const hasSecondary =
    overview.secondary_endpoints && overview.secondary_endpoints.length > 0;

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
        Trial at a glance
      </p>
      {overview.title && (
        <h3 className="text-lg font-semibold text-slate-900">{overview.title}</h3>
      )}
      {overview.short_description && (
        <p className="mt-1 text-sm text-slate-700">{overview.short_description}</p>
      )}

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <Field label="Phase" value={overview.phase} />
        <Field label="Indication" value={overview.indication} />
        <Field label="Sponsor" value={overview.sponsor} />
        <Field label="Design" value={overview.design} />
        <Field label="Duration" value={overview.treatment_duration} />
        <Field label="Target N" value={overview.sample_size} />
      </div>

      {hasArms && (
        <div className="mt-4">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Arms
          </p>
          <ul className="space-y-0.5 text-sm text-slate-800">
            {overview.arms.map((arm, i) => (
              <li key={i}>{arm}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {overview.primary_endpoint && (
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Primary endpoint
            </p>
            <p className="text-sm text-slate-800">{overview.primary_endpoint}</p>
          </div>
        )}
        {hasSecondary && (
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Secondary endpoints
            </p>
            <ul className="list-disc space-y-0.5 pl-4 text-sm text-slate-800">
              {overview.secondary_endpoints.map((ep, i) => (
                <li key={i}>{ep}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {overview.notable_aspects && (
        <div className="mt-4 rounded border-l-4 border-amber-400 bg-amber-50 p-3">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-amber-700">
            Notable aspects
          </p>
          <p className="text-sm text-slate-800">{overview.notable_aspects}</p>
        </div>
      )}
    </div>
  );
}
