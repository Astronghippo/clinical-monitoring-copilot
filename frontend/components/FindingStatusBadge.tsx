"use client";
import { useState } from "react";
import { ChevronDown } from "lucide-react";
import type { FindingStatus } from "@/lib/types";

const LABEL: Record<FindingStatus, string> = {
  open: "Open",
  in_review: "In review",
  resolved: "Resolved",
  false_positive: "False positive",
};

const STYLE: Record<FindingStatus, string> = {
  open: "bg-slate-100 text-slate-700",
  in_review: "bg-blue-100 text-blue-800",
  resolved: "bg-emerald-100 text-emerald-800",
  false_positive: "bg-neutral-200 text-neutral-600 line-through",
};

interface Props {
  value: FindingStatus;
  onChange: (next: FindingStatus) => Promise<void> | void;
  disabled?: boolean;
}

export function FindingStatusBadge({ value, onChange, disabled }: Props) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  async function pick(s: FindingStatus) {
    setOpen(false);
    if (s === value) return;
    setBusy(true);
    try {
      await onChange(s);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative inline-block">
      <button
        type="button"
        disabled={disabled || busy}
        onClick={() => setOpen((o) => !o)}
        className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium ${STYLE[value]} disabled:opacity-50`}
      >
        {LABEL[value]}
        <ChevronDown size={12} />
      </button>
      {open && (
        <div className="absolute left-0 z-20 mt-1 w-40 rounded-md border border-slate-200 bg-white py-1 text-sm shadow-lg">
          {(Object.keys(LABEL) as FindingStatus[]).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => pick(s)}
              className="block w-full px-3 py-1.5 text-left hover:bg-slate-50"
            >
              {LABEL[s]}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
