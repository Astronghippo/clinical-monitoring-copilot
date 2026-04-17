"use client";
import { useEffect, useState } from "react";

interface Props {
  /** Current backend status: "pending" | "running" | etc. */
  status: string;
  /** ISO timestamp the analysis was created (to compute elapsed time). */
  startedAt: string;
}

function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function phaseMessage(status: string, seconds: number): string {
  if (status === "pending") return "Queued — starting analyzers…";
  if (seconds < 10) return "Running visit-window checks (deterministic, fast)…";
  if (seconds < 45) return "Running completeness checks (Claude reasoning per visit)…";
  if (seconds < 90) return "Running eligibility checks (Claude reasoning per subject)…";
  return "Still running — complex datasets can take a bit longer…";
}

export function ProgressIndicator({ status, startedAt }: Props) {
  const [elapsed, setElapsed] = useState<number>(0);

  useEffect(() => {
    const startMs = new Date(startedAt).getTime();
    const update = () =>
      setElapsed(Math.max(0, Math.floor((Date.now() - startMs) / 1000)));
    update();
    const interval = setInterval(update, 500);
    return () => clearInterval(interval);
  }, [startedAt]);

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <p className="text-sm font-medium text-slate-900">
          {phaseMessage(status, elapsed)}
        </p>
        <span
          aria-label="elapsed time"
          className="font-mono text-sm tabular-nums text-slate-500"
        >
          {formatElapsed(elapsed)}
        </span>
      </div>
      <div
        role="progressbar"
        aria-label="Analysis in progress"
        className="relative h-2 overflow-hidden rounded-full bg-slate-100"
      >
        <div className="absolute inset-y-0 w-1/4 animate-progress-slide rounded-full bg-gradient-to-r from-slate-400 via-slate-600 to-slate-400" />
      </div>
      <p className="mt-3 text-xs text-slate-500">
        Three analyzers run in sequence. Typical completion: 30–90 seconds for
        ~20 subjects. Don&apos;t navigate away — results appear automatically
        when ready.
      </p>
    </div>
  );
}
