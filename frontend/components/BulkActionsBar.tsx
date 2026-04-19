"use client";
import type { FindingStatus } from "@/lib/types";

interface Props {
  count: number;
  onClear: () => void;
  onBulkStatus: (status: FindingStatus) => Promise<void>;
  onBulkDraftLetters: () => Promise<void>;
}

export function BulkActionsBar({ count, onClear, onBulkStatus, onBulkDraftLetters }: Props) {
  if (count === 0) return null;
  return (
    <div className="sticky top-0 z-30 flex items-center gap-3 rounded-lg border border-slate-300 bg-slate-900 px-4 py-2 text-sm text-white shadow-md">
      <span className="font-semibold">{count} selected</span>
      <div className="h-4 w-px bg-slate-600" />
      <button type="button" onClick={() => onBulkStatus("resolved")}
              className="rounded px-2 py-1 hover:bg-slate-800">
        Mark resolved
      </button>
      <button type="button" onClick={() => onBulkStatus("in_review")}
              className="rounded px-2 py-1 hover:bg-slate-800">
        Mark in review
      </button>
      <button type="button" onClick={() => onBulkStatus("false_positive")}
              className="rounded px-2 py-1 hover:bg-slate-800">
        False positive
      </button>
      <div className="h-4 w-px bg-slate-600" />
      <button type="button" onClick={onBulkDraftLetters}
              className="rounded bg-emerald-600 px-2 py-1 hover:bg-emerald-500">
        Draft {count} query letter{count === 1 ? "" : "s"}
      </button>
      <div className="flex-1" />
      <button type="button" onClick={onClear}
              className="text-slate-400 hover:text-white">
        Clear selection
      </button>
    </div>
  );
}
