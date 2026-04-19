"use client";
import { useRef, useState } from "react";
import { X } from "lucide-react";
import { api } from "@/lib/api";
import type { AmendmentDiff as AmendmentDiffType, Finding } from "@/lib/types";

interface Props {
  analysisId: number;
  findings: Finding[];
  onClose: () => void;
}

export function AmendmentDiff({ analysisId, findings, onClose }: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [diff, setDiff] = useState<AmendmentDiffType | null>(null);

  async function handleSubmit() {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setLoading(true);
    setError(null);
    setDiff(null);
    try {
      const result = await api.checkAmendment(analysisId, file);
      setDiff(result);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const hasChanges =
    diff &&
    (diff.added_visits.length > 0 ||
      diff.removed_visits.length > 0 ||
      diff.changed_visits.length > 0 ||
      diff.added_criteria.length > 0 ||
      diff.removed_criteria.length > 0 ||
      diff.obsolete_finding_ids.length > 0);

  // Map finding IDs to summaries for display.
  const findingById = new Map(findings.map((f) => [f.id, f]));

  return (
    <aside
      role="dialog"
      aria-label="Amendment diff"
      className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
    >
      <div className="mb-4 flex items-start justify-between">
        <h2 className="text-base font-semibold text-slate-800">Check Amendment</h2>
        <button
          aria-label="Close"
          onClick={onClose}
          className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
        >
          <X size={16} />
        </button>
      </div>

      <p className="mb-3 text-sm text-slate-600">
        Upload the amended protocol PDF to see which existing findings would be
        resolved by the changes.
      </p>

      <div className="mb-3 flex flex-col gap-2">
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,application/pdf"
          className="block w-full text-sm text-slate-600 file:mr-3 file:rounded file:border file:border-slate-200 file:bg-white file:px-3 file:py-1 file:text-sm file:text-slate-700 hover:file:bg-slate-50"
        />
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          Upload amended protocol
        </button>
      </div>

      {loading && (
        <p className="text-sm text-slate-500">Checking amendment — parsing protocol...</p>
      )}

      {error && (
        <p className="mt-2 rounded border border-red-200 bg-red-50 p-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {diff && !hasChanges && (
        <p className="mt-4 text-sm text-slate-600">No relevant changes detected.</p>
      )}

      {diff && hasChanges && (
        <div className="mt-4 space-y-4 text-sm">
          {diff.added_visits.length > 0 && (
            <section>
              <h3 className="mb-1 font-medium text-slate-700">Added visits</h3>
              <ul className="list-disc pl-5 text-slate-600">
                {diff.added_visits.map((v) => (
                  <li key={v}>{v}</li>
                ))}
              </ul>
            </section>
          )}

          {diff.removed_visits.length > 0 && (
            <section>
              <h3 className="mb-1 font-medium text-slate-700">Removed visits</h3>
              <ul className="list-disc pl-5 text-slate-600">
                {diff.removed_visits.map((v) => (
                  <li key={v}>{v}</li>
                ))}
              </ul>
            </section>
          )}

          {diff.changed_visits.length > 0 && (
            <section>
              <h3 className="mb-1 font-medium text-slate-700">Changed visits</h3>
              <ul className="list-disc pl-5 text-slate-600">
                {diff.changed_visits.map((v) => (
                  <li key={v}>{v}</li>
                ))}
              </ul>
            </section>
          )}

          {diff.removed_criteria.length > 0 && (
            <section>
              <h3 className="mb-1 font-medium text-slate-700">Removed eligibility criteria</h3>
              <ul className="list-disc pl-5 text-slate-600">
                {diff.removed_criteria.map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
            </section>
          )}

          {diff.added_criteria.length > 0 && (
            <section>
              <h3 className="mb-1 font-medium text-slate-700">Added eligibility criteria</h3>
              <ul className="list-disc pl-5 text-slate-600">
                {diff.added_criteria.map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
            </section>
          )}

          {diff.obsolete_finding_ids.length > 0 && (
            <section>
              <h3 className="mb-1 font-medium text-green-700">
                Obsolete findings: {diff.obsolete_finding_ids.length} finding
                {diff.obsolete_finding_ids.length !== 1 ? "s" : ""} would be resolved
                by this amendment
              </h3>
              <ul className="list-disc pl-5 text-slate-600">
                {diff.obsolete_finding_ids.map((id) => {
                  const f = findingById.get(id);
                  return (
                    <li key={id}>
                      {f ? `#${id}: ${f.summary}` : `Finding #${id}`}
                    </li>
                  );
                })}
              </ul>
            </section>
          )}
        </div>
      )}
    </aside>
  );
}
