"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { QueryLetter } from "@/lib/types";

interface Props {
  findingIds: number[];
  onClose: () => void;
}

type LetterResult =
  | { status: "fulfilled"; value: QueryLetter }
  | { status: "rejected"; reason: unknown };

export function BulkLetterModal({ findingIds, onClose }: Props) {
  const total = findingIds.length;
  const [doneCount, setDoneCount] = useState(0);
  const [results, setResults] = useState<LetterResult[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    const settled: LetterResult[] = new Array(total);
    let completed = 0;

    findingIds.forEach((id, idx) => {
      api
        .draftQueryLetter(id)
        .then((letter) => {
          if (cancelled) return;
          settled[idx] = { status: "fulfilled", value: letter };
          completed += 1;
          setDoneCount(completed);
          if (completed === total) {
            setResults([...settled]);
          }
        })
        .catch((err: unknown) => {
          if (cancelled) return;
          settled[idx] = { status: "rejected", reason: err };
          completed += 1;
          setDoneCount(completed);
          if (completed === total) {
            setResults([...settled]);
          }
        });
    });

    return () => {
      cancelled = true;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const isDone = results !== null;

  const successfulLetters: QueryLetter[] = isDone
    ? (results
        .filter((r): r is { status: "fulfilled"; value: QueryLetter } => r.status === "fulfilled")
        .map((r) => r.value))
    : [];

  const failedCount = isDone ? results.filter((r) => r.status === "rejected").length : 0;

  function handleDownload() {
    const body = successfulLetters
      .map((l) => `Subject: ${l.subject_line}\n\n${l.body}\n\nReply by: ${l.reply_by}`)
      .join("\n\n=====\n\n");
    const blob = new Blob([body], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "query-letters.txt";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40"
      role="presentation"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Bulk query letter drafting"
        className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="mb-4 text-lg font-semibold text-slate-900">
          Bulk Query Letter Drafting
        </h2>

        {!isDone && (
          <p className="text-slate-700">
            Drafting letter {doneCount + 1} of {total}…
          </p>
        )}

        {isDone && (
          <div className="space-y-4">
            {failedCount > 0 && (
              <p className="text-amber-700">
                {failedCount} letter{failedCount === 1 ? "" : "s"} failed
              </p>
            )}
            {successfulLetters.length > 0 && (
              <p className="text-slate-700">
                {successfulLetters.length} letter{successfulLetters.length === 1 ? "" : "s"} ready.
              </p>
            )}
          </div>
        )}

        <div className="mt-6 flex gap-3 justify-end">
          {isDone && successfulLetters.length > 0 && (
            <button
              type="button"
              onClick={handleDownload}
              className="rounded bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500"
            >
              Download .txt
            </button>
          )}
          <button
            type="button"
            onClick={onClose}
            className="rounded border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
