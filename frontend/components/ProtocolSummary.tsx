"use client";
import { useState } from "react";
import type { EligibilityCriterion, ProtocolSpec, VisitDef } from "@/lib/types";
import { api } from "@/lib/api";

interface Props {
  spec: ProtocolSpec;
  protocolId: number;
  onSpecUpdated?: (spec: ProtocolSpec) => void;
}

function formatWindow(minus: number, plus: number): string {
  if (minus === 0 && plus === 0) return "no window";
  if (minus === plus) return `±${plus} day${plus === 1 ? "" : "s"}`;
  return `-${minus} / +${plus} days`;
}

function newVisit(): VisitDef {
  return {
    visit_id: `V${Date.now()}`,
    name: "",
    nominal_day: 0,
    window_minus_days: 0,
    window_plus_days: 0,
    required_procedures: [],
  };
}

function newCriterion(): EligibilityCriterion {
  return {
    criterion_id: `C${Date.now()}`,
    kind: "inclusion",
    text: "",
  };
}

function deepClone<T>(v: T): T {
  return JSON.parse(JSON.stringify(v)) as T;
}

export function ProtocolSummary({ spec, protocolId, onSpecUpdated }: Props) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<ProtocolSpec>(() => deepClone(spec));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const inclusions = spec.eligibility.filter((c) => c.kind === "inclusion");
  const exclusions = spec.eligibility.filter((c) => c.kind === "exclusion");

  function handleEdit() {
    setDraft(deepClone(spec));
    setError(null);
    setEditing(true);
  }

  function handleCancel() {
    setEditing(false);
    setError(null);
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const result = await api.patchProtocolSpec(protocolId, draft);
      if (onSpecUpdated && result.spec_json) {
        onSpecUpdated(result.spec_json as ProtocolSpec);
      }
      setEditing(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  // --- Visit edit helpers ---
  function updateVisit(idx: number, field: keyof VisitDef, value: string | number) {
    setDraft((prev) => {
      const visits = prev.visits.map((v, i) =>
        i === idx ? { ...v, [field]: value } : v,
      );
      return { ...prev, visits };
    });
  }

  function addVisit() {
    setDraft((prev) => ({ ...prev, visits: [...prev.visits, newVisit()] }));
  }

  function removeVisit(idx: number) {
    setDraft((prev) => ({
      ...prev,
      visits: prev.visits.filter((_, i) => i !== idx),
    }));
  }

  // --- Eligibility edit helpers ---
  function updateCriterion(
    idx: number,
    field: keyof EligibilityCriterion,
    value: string,
  ) {
    setDraft((prev) => {
      const eligibility = prev.eligibility.map((c, i) =>
        i === idx ? { ...c, [field]: value } : c,
      );
      return { ...prev, eligibility };
    });
  }

  function addCriterion() {
    setDraft((prev) => ({
      ...prev,
      eligibility: [...prev.eligibility, newCriterion()],
    }));
  }

  function removeCriterion(idx: number) {
    setDraft((prev) => ({
      ...prev,
      eligibility: prev.eligibility.filter((_, i) => i !== idx),
    }));
  }

  if (!editing) {
    // ---- View mode ----
    return (
      <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm">
        <div className="mb-3 flex items-center justify-between">
          <p className="text-slate-600">
            Claude extracted the following structure from your protocol. Verify it
            looks right before running analysis.
          </p>
          <button
            onClick={handleEdit}
            className="ml-4 shrink-0 rounded border border-slate-300 bg-white px-2 py-1 text-xs text-slate-700 hover:bg-slate-100"
            aria-label="Edit protocol spec"
          >
            Edit
          </button>
        </div>

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

  // ---- Edit mode ----
  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm">
      <div className="mb-3 flex items-center justify-between">
        <p className="font-medium text-blue-800">Editing protocol spec</p>
        <div className="flex gap-2">
          <button
            onClick={handleCancel}
            disabled={saving}
            className="rounded border border-slate-300 bg-white px-3 py-1 text-xs text-slate-700 hover:bg-slate-100 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="rounded bg-blue-600 px-3 py-1 text-xs text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save changes"}
          </button>
        </div>
      </div>

      {error && (
        <p className="mb-3 rounded border border-red-200 bg-red-50 px-2 py-1 text-xs text-red-700">
          {error}
        </p>
      )}

      {/* Visits section */}
      <div className="mb-4">
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Visits
        </h4>
        <div className="space-y-2">
          {draft.visits.map((v, idx) => (
            <div
              key={v.visit_id}
              className="flex flex-wrap items-center gap-2 rounded border border-slate-200 bg-white p-2 text-xs"
            >
              <span className="font-mono text-slate-400">{v.visit_id}</span>
              <input
                aria-label={`Visit ${idx + 1} name`}
                className="flex-1 rounded border border-slate-200 px-1 py-0.5"
                value={v.name}
                onChange={(e) => updateVisit(idx, "name", e.target.value)}
                placeholder="Name"
              />
              <label className="flex items-center gap-1">
                Day
                <input
                  aria-label={`Visit ${idx + 1} nominal day`}
                  type="number"
                  className="w-16 rounded border border-slate-200 px-1 py-0.5"
                  value={v.nominal_day}
                  onChange={(e) =>
                    updateVisit(idx, "nominal_day", Number(e.target.value))
                  }
                />
              </label>
              <label className="flex items-center gap-1">
                −
                <input
                  aria-label={`Visit ${idx + 1} window minus`}
                  type="number"
                  className="w-12 rounded border border-slate-200 px-1 py-0.5"
                  value={v.window_minus_days}
                  onChange={(e) =>
                    updateVisit(idx, "window_minus_days", Number(e.target.value))
                  }
                />
              </label>
              <label className="flex items-center gap-1">
                +
                <input
                  aria-label={`Visit ${idx + 1} window plus`}
                  type="number"
                  className="w-12 rounded border border-slate-200 px-1 py-0.5"
                  value={v.window_plus_days}
                  onChange={(e) =>
                    updateVisit(idx, "window_plus_days", Number(e.target.value))
                  }
                />
              </label>
              <button
                onClick={() => removeVisit(idx)}
                className="ml-auto text-red-500 hover:text-red-700"
                aria-label={`Remove visit ${idx + 1}`}
              >
                ✕
              </button>
            </div>
          ))}
          <button
            onClick={addVisit}
            className="rounded border border-dashed border-blue-300 px-3 py-1 text-xs text-blue-600 hover:bg-blue-50"
          >
            + Add visit
          </button>
        </div>
      </div>

      {/* Eligibility section */}
      <div>
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Eligibility criteria
        </h4>
        <div className="space-y-2">
          {draft.eligibility.map((c, idx) => (
            <div
              key={c.criterion_id}
              className="flex items-start gap-2 rounded border border-slate-200 bg-white p-2 text-xs"
            >
              <span className="shrink-0 font-mono text-slate-400">{c.criterion_id}</span>
              <select
                aria-label={`Criterion ${idx + 1} kind`}
                className="rounded border border-slate-200 px-1 py-0.5"
                value={c.kind}
                onChange={(e) =>
                  updateCriterion(idx, "kind", e.target.value as "inclusion" | "exclusion")
                }
              >
                <option value="inclusion">Inclusion</option>
                <option value="exclusion">Exclusion</option>
              </select>
              <textarea
                aria-label={`Criterion ${idx + 1} text`}
                className="flex-1 rounded border border-slate-200 px-1 py-0.5"
                rows={2}
                value={c.text}
                onChange={(e) => updateCriterion(idx, "text", e.target.value)}
              />
              <button
                onClick={() => removeCriterion(idx)}
                className="shrink-0 text-red-500 hover:text-red-700"
                aria-label={`Remove criterion ${idx + 1}`}
              >
                ✕
              </button>
            </div>
          ))}
          <button
            onClick={addCriterion}
            className="rounded border border-dashed border-blue-300 px-3 py-1 text-xs text-blue-600 hover:bg-blue-50"
          >
            + Add criterion
          </button>
        </div>
      </div>
    </div>
  );
}
