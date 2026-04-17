"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import type { Protocol } from "@/lib/types";

export function ProtocolUploader({ onUploaded }: { onUploaded: (p: Protocol) => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="mb-2 text-lg font-semibold">1. Upload protocol (PDF)</h2>
      <input
        type="file"
        accept="application/pdf"
        disabled={busy}
        data-testid="protocol-input"
        onChange={async (e) => {
          const f = e.target.files?.[0];
          if (!f) return;
          setBusy(true);
          setError(null);
          try {
            onUploaded(await api.uploadProtocol(f));
          } catch (err) {
            setError((err as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      />
      {busy && <p className="mt-2 text-sm text-slate-500">Extracting protocol…</p>}
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </div>
  );
}
