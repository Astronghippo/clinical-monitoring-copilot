"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import type { Analysis } from "@/lib/types";

interface Props {
  protocolId: number | null;
  datasetId: number | null;
  onStarted: (a: Analysis) => void;
}

export function RunAnalysisButton({ protocolId, datasetId, onStarted }: Props) {
  const [busy, setBusy] = useState(false);
  const disabled = busy || protocolId == null || datasetId == null;

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="mb-2 text-lg font-semibold">3. Run analysis</h2>
      <button
        type="button"
        className="rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        disabled={disabled}
        onClick={async () => {
          if (protocolId == null || datasetId == null) return;
          setBusy(true);
          try {
            onStarted(await api.runAnalysis(protocolId, datasetId));
          } finally {
            setBusy(false);
          }
        }}
      >
        {busy ? "Starting…" : "Run analysis"}
      </button>
    </div>
  );
}
