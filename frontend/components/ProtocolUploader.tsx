"use client";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { Protocol } from "@/lib/types";

function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function ProtocolUploader({ onUploaded }: { onUploaded: (p: Protocol) => void }) {
  const [parsing, setParsing] = useState<Protocol | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef<number | null>(null);

  // Tick the elapsed counter while a parse is in flight.
  useEffect(() => {
    if (!parsing) return;
    startRef.current = Date.now();
    setElapsed(0);
    const interval = setInterval(() => {
      if (startRef.current)
        setElapsed(Math.floor((Date.now() - startRef.current) / 1000));
    }, 500);
    return () => clearInterval(interval);
  }, [parsing?.id]);

  // Poll GET /protocols/{id} until parse_status !== "parsing".
  useEffect(() => {
    if (!parsing || parsing.parse_status !== "parsing") return;
    let live = true;
    async function tick() {
      try {
        const updated = await api.getProtocol(parsing!.id);
        if (!live) return;
        if (updated.parse_status === "parsing") {
          setTimeout(tick, 2000);
          return;
        }
        setParsing(null);
        if (updated.parse_status === "error") {
          setError(updated.parse_error ?? "Parse failed");
          return;
        }
        onUploaded(updated);
      } catch (err) {
        if (live) setError((err as Error).message);
      }
    }
    tick();
    return () => {
      live = false;
    };
  }, [parsing?.id, parsing?.parse_status, onUploaded]);

  const busy = parsing !== null;

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
          setError(null);
          try {
            const p = await api.uploadProtocol(f);
            if (p.parse_status === "done" && p.spec_json) {
              // Small / fast protocols may already be done on upload return.
              onUploaded(p);
            } else {
              setParsing(p);
            }
          } catch (err) {
            setError((err as Error).message);
          }
        }}
      />

      {busy && (
        <div className="mt-3 space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-slate-700">
              Claude is reading the protocol… this can take up to a minute for
              long trials.
            </span>
            <span className="font-mono text-xs tabular-nums text-slate-500">
              {formatElapsed(elapsed)}
            </span>
          </div>
          <div
            role="progressbar"
            aria-label="Parsing protocol"
            className="relative h-1.5 overflow-hidden rounded-full bg-slate-100"
          >
            <div className="absolute inset-y-0 w-1/4 animate-progress-slide rounded-full bg-gradient-to-r from-slate-400 via-slate-600 to-slate-400" />
          </div>
        </div>
      )}

      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </div>
  );
}
