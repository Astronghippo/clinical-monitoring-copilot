"use client";
import React from "react";
import type { Finding } from "@/lib/types";

export function FindingDetail({
  finding,
  onClose,
}: {
  finding: Finding;
  onClose: () => void;
}) {
  return (
    <aside className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between">
        <h3 className="text-lg font-semibold">{finding.summary}</h3>
        <button
          type="button"
          aria-label="Close"
          className="text-slate-400 hover:text-slate-700"
          onClick={onClose}
        >
          ×
        </button>
      </div>
      <p className="mt-2 text-sm text-slate-600">{finding.detail}</p>
    </aside>
  );
}
