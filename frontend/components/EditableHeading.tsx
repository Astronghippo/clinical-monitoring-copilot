"use client";
import { useEffect, useRef, useState } from "react";
import { Pencil } from "lucide-react";

interface Props {
  /** Current name. null → show `fallback` instead. */
  value: string | null;
  /** What to show when value is null (e.g. "Analysis #10"). */
  fallback: string;
  /** Persists the new name. Called with null when user clears the field. */
  onSave: (next: string | null) => Promise<void>;
}

/** Heading that switches to an input on click. Saves on blur or Enter, cancels on Escape. */
export function EditableHeading({ value, fallback, onSave }: Props) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    setDraft(value ?? "");
  }, [value]);

  useEffect(() => {
    if (editing) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [editing]);

  async function commit() {
    const trimmed = draft.trim();
    const next = trimmed === "" ? null : trimmed;
    // No-op if unchanged.
    if (next === value) {
      setEditing(false);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onSave(next);
      setEditing(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  function cancel() {
    setDraft(value ?? "");
    setEditing(false);
    setError(null);
  }

  if (!editing) {
    return (
      <div className="group inline-flex items-center gap-2">
        <h1 className="text-2xl font-bold">{value ?? fallback}</h1>
        <button
          type="button"
          onClick={() => setEditing(true)}
          aria-label="Rename analysis"
          className="rounded p-1 text-slate-400 opacity-0 transition hover:bg-slate-100 hover:text-slate-700 group-hover:opacity-100 focus:opacity-100"
        >
          <Pencil size={16} />
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1">
      <input
        ref={inputRef}
        type="text"
        value={draft}
        disabled={saving}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            commit();
          } else if (e.key === "Escape") {
            cancel();
          }
        }}
        placeholder={fallback}
        className="rounded border border-slate-300 px-2 py-1 text-2xl font-bold focus:border-slate-500 focus:outline-none"
      />
      <span className="text-xs text-slate-500">
        Enter to save · Esc to cancel · empty to reset to {fallback}
      </span>
      {error && <span className="text-xs text-red-600">{error}</span>}
    </div>
  );
}
