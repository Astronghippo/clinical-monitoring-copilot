"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import type { Dataset } from "@/lib/types";

export function DatasetUploader({ onUploaded }: { onUploaded: (d: Dataset) => void }) {
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState("demo-dataset");
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="mb-2 text-lg font-semibold">2. Upload dataset</h2>
      <input
        className="mr-3 rounded border px-2 py-1 text-sm"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Dataset name"
      />
      <input
        type="file"
        accept=".csv"
        multiple
        disabled={busy}
        data-testid="dataset-input"
        onChange={async (e) => {
          const files = Array.from(e.target.files ?? []);
          if (files.length === 0) return;
          setBusy(true);
          setError(null);
          try {
            onUploaded(await api.uploadDataset(name, files));
          } catch (err) {
            setError((err as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      />
      <p className="mt-2 text-xs text-slate-500">
        Accepts either (a) four SDTM files — dm.csv, sv.csv, vs.csv
        (+ optional ex.csv) — OR (b) one combined CSV in wide format
        (Subject_ID + Visit + Lab_* columns, e.g. a Medidata Rave export).
      </p>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </div>
  );
}
